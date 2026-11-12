import pandas as pd
import numpy as np

def _black_plot(df, dminc, dm_rrr, mort, ut, intervention, annual_overall, once_off_st, cycle):
    df = pd.merge(df, dminc, on=['age', 'sex', 'sq', 'DM'], how='left')
    df['rate']*=(1-(dm_rrr/100))
    df['tp'] = 1 - np.exp(-df['rate'])
    df['case'] = df['N']*df['tp']
    df = df[['age', 'sex', 'sq', 'DM', 'N', 'case']]
    df.loc[df['case'].isna(), 'case'] = 0
    df['yll'] = df['N']
    df = df.sort_values(by=['age', 'sex', 'sq', 'DM'])
    case_1 = df.groupby(['age', 'sex', 'sq'])['case'].shift(1)
    condition = (df['DM'] == 1) & case_1.notna()
    df.loc[condition, 'N'] += case_1[condition]
    df.loc[condition, 'yll'] += 0.5*case_1[condition]
    df.loc[df['DM']==0, 'N'] -= df['case']
    df.loc[df['DM']==0, 'yll'] -= 0.5*df['case']
    df = pd.merge(df, mort, on=['age', 'sex', 'sq', 'DM'], how='left')
    df['death'] = df['tp']*df['N']
    df.loc[df['death'].isna(), 'death'] = 0
    df['N'] -= df['death']
    df['yll'] -= 0.5*df['death']
    df = df[['age', 'sex', 'sq', 'DM', 'N', 'case', 'yll', 'death']]

    df = pd.merge(df, ut, on=['age','sex'], how='left')
    df['qaly']=0.0
    df.loc[df['DM']==0, 'qaly'] = df['yll']*df['UT']
    df.loc[df['DM']==1, 'qaly'] = df['yll']*df['UT']*0.785
    df['hccost']=0.0
    df.loc[df['DM']==1, 'hccost'] = df['yll']*5007.42
    df['intcost']=0.0
    if intervention == 1:
        length = len(df)
        annov = annual_overall/length
        df['intcost'] = annov
        if cycle==1:
            oncof = once_off_st/length
            df['intcost'] += oncof
    df['tcost'] = df['hccost'] + df['intcost']
    return df

def _falconist(df, births, cycle):

    # Migration
    count = df['N'].sum()
    df['N'] *= (1+(225000/count))

    # Age a year, add births
    df.loc[df['age'] < 100, 'age'] = df['age']+1
    birth = births.loc[births['year'] == cycle]
    birth = birth[['age', 'sex', 'sq', 'DM', 'N']]
    df = df[['age', 'sex', 'sq', 'DM', 'N']]
    df = pd.concat([df, birth], ignore_index=True)
    df = df.groupby(['age', 'sex', 'sq', 'DM'], as_index=False)['N'].sum()

    return df

def pax(ncycles, dm_rrr, compint, annual_overall, once_off_st, age_lb, age_ub, discounting):

    init = pd.read_csv('prevpop2020.csv')
    births = pd.read_csv('Births.csv')
    dminc = pd.read_csv('DMINC.csv')
    mort = pd.read_csv('ALLMORT.csv')
    ut = pd.read_csv('utg.csv')

    df = init
    tracking = []

    for i in range(1, ncycles+1):

        df = _black_plot(df=df, 
                         dminc=dminc, 
                         dm_rrr=dm_rrr, 
                         mort=mort, 
                         ut=ut, 
                         intervention=compint, 
                         annual_overall=annual_overall, 
                         once_off_st=once_off_st,
                         cycle=i)

        df_sub = df.loc[(df['age'] >= age_lb) & (df['age'] <= age_ub)]
        df_sub = df_sub.groupby(['sex', 'sq'], as_index=False)[['case', 'death', 'yll', 'qaly', 'hccost', 'intcost', 'tcost']].sum()
        df_sub['cycle'] = i
        tracking.append(df_sub)

        df = _falconist(df=df,
                        births=births,
                        cycle=i)

    df = pd.concat(tracking, ignore_index=True)

    if discounting!=0:
        dc = discounting/100
        dc_values = ['yll', 'qaly', 'hccost', 'intcost', 'tcost']
        for var in dc_values:
            df[f'{var}'] = df[f'{var}']/((1+dc)**(df['cycle']-1))

    df = df.groupby(['sex', 'sq'], as_index=False)[['case', 'death', 'yll', 'qaly', 'hccost', 'intcost', 'tcost']].sum()
    df['compint']=compint

    return df

