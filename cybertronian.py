import pandas as pd
import numpy as np
# import time
import warnings
from pandas.errors import PerformanceWarning
import plotly.express as px
import plotly.io as pio
import json
import plotly.utils
import plotly.graph_objects as go

def _events(df, tp_lt, a1c_r, mi_rrr, hf_rrr, st_rrr, pd_rrr, eskd_rrr, hypo_rrr, hype_rrr, cvdeath_rrr, redeath_rrr):

    df = pd.merge(df, tp_lt, on=['age', 'sex', 'sq', 'hstate'], how='inner')

    #Define outcomes
    outcomes = ['mi', 'hf', 'st', 'pd', 'eskd', 'hypo', 'hype', 'cvdeath', 'redeath', 'nondeath']
    event_cols = [f'{oc}_event' for oc in outcomes]

    df['rate_mi']*=np.exp(0.1508*a1c_r)
    df['rate_hf']*=np.exp(0.1744*a1c_r)
    df['rate_st']*=np.exp(0.1278*a1c_r)
    df['rate_pd']*=np.exp(0.5621*a1c_r)
    df['rate_eskd']*=np.exp(0.4943*a1c_r)
    df['rate_cvdeath']*=np.exp(0.1508*a1c_r)
    df['rate_redeath']*=np.exp(0.4943*a1c_r)
            
    df['rate_mi']*=(1-(mi_rrr/100))
    df['rate_hf']*=(1-(hf_rrr/100))
    df['rate_st']*=(1-(st_rrr/100))
    df['rate_pd']*=(1-(pd_rrr/100))
    df['rate_eskd']*=(1-(eskd_rrr/100))
    df['rate_hypo']*=(1-(hypo_rrr/100))
    df['rate_hype']*=(1-(hype_rrr/100))
    df['rate_cvdeath']*=(1-(cvdeath_rrr/100))
    df['rate_redeath']*=(1-(redeath_rrr/100))

    rate_cols = [f"rate_{outcome}" for outcome in outcomes]
    df["ratesum"] = df[rate_cols].sum(axis=1)

    df["tp_sum"] = 1 - np.exp(-df["ratesum"])

    for outcome in outcomes:
        df[f"tp_{outcome}"] = df["tp_sum"] * (df[f"rate_{outcome}"] / df["ratesum"])

    #Outcomes
    for oc in outcomes:
        df[f'{oc}_event'] = df['count'] * df[f'tp_{oc}']

    #Drop rates and transition probabilities
    rate_cols = [col for col in df.columns if col.startswith('rate_')]
    tp_cols = [col for col in df.columns if col.startswith('tp_')]
    df = df.drop(columns=rate_cols)
    df = df.drop(columns=tp_cols)

    #Replicate count variable
    df['new_count'] = df['count'].copy()

    return df

def _apply_markov_transitions(df, transition_maps, death_transitions):

    for event_col, state_pairs in transition_maps.items():
        for src, dest in state_pairs:
            #People who leave the health state
            leaving = (df['hstate'] == src) * df[event_col]

            #Essentially just replicate the value across the age/sex/sq
            added = leaving.groupby([df['age'], df['sex'], df['sq']]).transform('sum')
            
            # Subtract from origin, add to destination
            df.loc[df['hstate'] == src, 'new_count'] -= leaving
            df.loc[df['hstate'] == dest, 'new_count'] += added * (df['hstate'] == dest)

    # Process death events (absorbing states 33, 34, 35)
    for death_event, dest_state in death_transitions.items():
        leaving = (df['hstate'] <= 32) * df[death_event]
        added = leaving.groupby([df['age'], df['sex'], df['sq']]).transform('sum')
        
        df.loc[df['hstate'] <= 32, 'new_count'] -= leaving
        df.loc[df['hstate'] == dest_state, 'new_count'] += added * (df['hstate'] == dest_state)

    #Age cohort, capped at 100
    df['age'] = (df['age'] + 1).clip(upper=100)
    df = df.groupby(['age', 'sex', 'sq', 'hstate'], as_index=False).sum()

    return df

def _newdm(df, pop, dm_inc, pr_inc, cycle):
    #Add incident diabetes

    #Keep alive
    df_sub = df.loc[df['hstate'] <= 32]

    #Lose health states/collapse
    df_sub = df_sub.groupby(['age', 'sex', 'sq'], as_index=False)['new_count'].sum()

    #Population for the cycle
    pop_c = pop.loc[pop['cycle'] == cycle]
    pop_c = pop_c.drop(columns='cycle')

    #Combine
    df_sub = pd.merge(df_sub, pop_c, on=['age', 'sex', 'sq'], how='outer')
    df_sub.loc[df_sub['new_count'].isna(), 'new_count'] = 0
    df_sub = pd.merge(df_sub, dm_inc, on=['age', 'sex', 'sq'], how='inner')

    #Clean in case of mismatch
    df_sub.loc[df_sub['pop'] < df_sub['new_count'], 'pop'] = df_sub['new_count']

    #New diabetes
    df_sub['no_dm'] = df_sub['pop'] - df_sub['new_count']
    df_sub['new_dm'] = df_sub['no_dm'] * df_sub['dm_tp']

    #Apportion to health states
    df_sub = pd.merge(pr_inc, df_sub, on=['age', 'sex', 'sq'], how='left')
    df_sub['total'] = df_sub.groupby(['age', 'sex', 'sq'])['pr'].transform('sum')
    df_sub['case'] = df_sub['new_dm'] * df_sub['pr'] / df_sub['total']

    #Final new case dataset
    df_sub = df_sub[['age', 'sex', 'sq', 'hstate', 'case']]

    #Add death states
    strata = df_sub[['age', 'sex', 'sq']].drop_duplicates()

    new_states = pd.DataFrame({'hstate': [33, 34, 35]})
    padding = strata.merge(new_states, how='cross')
    padding['case'] = 0.0

    df_sub = (
        pd.concat([df_sub, padding], ignore_index=True)
        .sort_values(by=['age', 'sex', 'sq', 'hstate'], ignore_index=True)
    )

    #Merge new cases in
    df = pd.merge(df, df_sub, on=['age', 'sex', 'sq', 'hstate'], how='outer')
    df = df.fillna(0)
    
    return df

def _utandcost(df, ut, cost, age_lb, age_ub, cycle, intervention, once_off_ind, once_off_st, annual_ind, annual_overall):
    #Merge in utilities and costs
    df = pd.merge(df, ut, on=['age', 'sex', 'sq', 'hstate'], how='inner')
    df = pd.merge(df, cost, on=['age', 'sex', 'sq', 'hstate'], how='inner')

    #QALYs and costs calculated using half of the person-years in the starting and ending health state each.
    df['yll'] = 0.5*(df['count'] + df['new_count'] + df['case'])
    df['qaly'] = (0.5*df['hstate_ut_pe']*(df['count'] + df['new_count'] + df['case']))+(df['hypo_event']*df['dis_hypo_pe'])+(df['hype_event']*df['dis_hype_pe'])
    df['hccost'] = (0.5*df['cycle_cost']*(df['count'] + df['new_count'] + df['case']))+ 10566*df['hypo_event'] + 11347*df['hype_event']+ 25273*df['mi_event'] + 24986*df['st_event'] + 19587*df['hf_event'] + 23727*df['pd_event'] + 17786*df['cvdeath_event']
    df['death_event'] = df['cvdeath_event'] + df['redeath_event'] + df['nondeath_event']


    df_sub = df.loc[df['hstate'] <= 32]
    df_sub = df_sub.loc[(df_sub['age'] >= age_lb) & (df_sub['age'] <= age_ub)]

    #Intervention costs
    if intervention == 1:
        length = len(df_sub)

        #1. once off for every individual
        if (cycle == 1):
            df_sub['intcost'] = once_off_ind*df_sub['case'] + once_off_ind*df_sub['count']
        else:
            df_sub['intcost'] = once_off_ind*df_sub['case']

        #2. once off at the start
        if (cycle == 1):
            onceoff = once_off_st/length
            df_sub['intcost'] = df_sub['intcost'] + onceoff

        #3. annual by individual
        df_sub['intcost'] = df_sub['intcost'] + df_sub['yll']*annual_ind

        #4. Annual overall
        annov = annual_overall/length
        df_sub['intcost'] = df_sub['intcost'] + annov
    else:
        df_sub['intcost'] = 0

    df_sub['tcost'] = df_sub['hccost'] + df_sub['intcost']

    #Results for the cycle in the df_sub dataframe.
    df_sub = df_sub.groupby(['sex', 'sq'], as_index=False)[['count', 'mi_event', 'hf_event', 'st_event', 'pd_event', 'eskd_event', 'hypo_event', 'hype_event', 'death_event', 'new_count', 'case', 'yll', 'qaly', 'hccost', 'intcost', 'tcost']].sum()

    #Prepare dataframe for next cycle
    df.loc[df['new_count'].isna(), 'new_count'] = 0
    df.loc[df['case'].isna(), 'case'] = 0
    df['count2'] = df['new_count'] + df['case']
    df = df[['age', 'sex', 'sq', 'hstate', 'count2']]
    df = df.rename(columns={'count2': 'count'})
    return df, df_sub

def cybertronian(age_lb, age_ub, a1c_r, mi_rrr, hf_rrr, st_rrr, pd_rrr, eskd_rrr, hypo_rrr, hype_rrr, cvdeath_rrr, redeath_rrr, fc_pp, fc_t, ac_pp, ac_t, ncycles, discounting):

    #Load the initial data
    lt_init = pd.read_csv('lt_init_1.csv')
    tp_lt = pd.read_csv('tp_lt_1.csv')
    pop = pd.read_csv('pop_1.csv')
    dm_inc = pd.read_csv('dm_inc_rates_1.csv')
    pr_inc = pd.read_csv('pr_hstate_inc_1.csv')
    ut = pd.read_csv('utilities_1.csv')
    cost = pd.read_csv('costs_1.csv')

    #State transitions
    transition_maps = {
        'mi_event': [
            (1, 2), (3, 7), (4, 8), (5, 9), (6, 10), (11, 17), (12, 18), 
            (13, 19), (14, 22), (15, 23), (16, 24), (20, 27), (21, 29), 
            (25, 30), (26, 28), (31, 32)
        ],
        'hf_event': [
            (1, 5), (2, 9), (3, 12), (4, 14), (6, 16), (7, 18), (8, 22), 
            (10, 24), (11, 20), (13, 21), (15, 25), (17, 27), (19, 29), 
            (23, 30), (26, 31), (28, 32)
        ],
        'st_event': [
            (1, 3), (2, 7), (4, 11), (5, 12), (6, 13), (8, 17), (9, 18),
            (10, 19), (14, 20), (15, 26), (16, 21), (22, 27), (23, 28),
            (24, 29), (25, 31), (30, 32)
        ],
        'pd_event': [
            (1, 4), (2, 8), (3, 11), (5, 14), (6, 15), (7, 17), (9, 22),
            (10, 23), (12, 20), (13, 26), (16, 25), (18, 27), (19, 28),
            (21, 31), (24, 30), (29, 32)
        ],
        'eskd_event': [
            (1, 6), (2, 10), (3, 13), (4, 15), (5, 16), (7, 19), (8, 23),
            (9, 24), (11, 26), (12, 21), (14, 25), (17, 28), (18, 29),
            (20, 31), (22, 30), (27, 32)
        ]
    }
    death_transitions = {
        'cvdeath_event': 33,
        'redeath_event': 34,
        'nondeath_event': 35
    }

    #Run cycles

    # mi_rrr=9
    # hf_rrr=33
    # st_rrr=2
    # pd_rrr=0
    # eskd_rrr=35
    # hypo_rrr=20
    # hype_rrr=0
    # cvdeath_rrr=9
    # redeath_rrr=35

    # age_lb=20
    # age_ub=100

    #Just make costs 0 if they aren't selected, means never double counting
    once_off_ind=fc_pp
    once_off_st=fc_t
    annual_ind=ac_pp
    annual_overall=ac_t

    df_c = lt_init
    df_i = lt_init
    tracking_c = []
    tracking_i = []
    for i in range(1,ncycles+1):

        df_c = _events(df=df_c, 
                             tp_lt=tp_lt,
                             a1c_r=0, 
                             mi_rrr=0, 
                             hf_rrr=0, 
                             st_rrr=0, 
                             pd_rrr=0, 
                             eskd_rrr=0, 
                             hypo_rrr=0, 
                             hype_rrr=0, 
                             cvdeath_rrr=0, 
                             redeath_rrr=0)
        
        df_c = _apply_markov_transitions(df=df_c, 
                                         transition_maps=transition_maps, 
                                         death_transitions=death_transitions)
        
        df_c = _newdm(df=df_c, 
                      pop=pop, 
                      dm_inc=dm_inc, 
                      pr_inc=pr_inc, 
                      cycle=i)
        
        df_c, df_sub_c = _utandcost(df=df_c, 
                                    ut=ut, 
                                    cost=cost, 
                                    age_lb=age_lb, 
                                    age_ub=age_ub, 
                                    cycle=i,
                                    intervention=0,
                                    once_off_ind=once_off_ind, 
                                    once_off_st=once_off_st, 
                                    annual_ind=annual_ind, 
                                    annual_overall=annual_overall)
        
        df_sub_c['cycle'] = i
        df_sub_c['compint'] = 0
        tracking_c.append(df_sub_c)

        df_i = _events(df=df_i, 
                     tp_lt=tp_lt,
                     a1c_r=a1c_r,
                     mi_rrr=mi_rrr, 
                     hf_rrr=hf_rrr, 
                     st_rrr=st_rrr, 
                     pd_rrr=pd_rrr, 
                     eskd_rrr=eskd_rrr, 
                     hypo_rrr=hypo_rrr, 
                     hype_rrr=hype_rrr, 
                     cvdeath_rrr=cvdeath_rrr, 
                     redeath_rrr=redeath_rrr)
        
        df_i = _apply_markov_transitions(df=df_i, 
                                         transition_maps=transition_maps, 
                                         death_transitions=death_transitions)
        
        df_i = _newdm(df=df_i, 
                      pop=pop, 
                      dm_inc=dm_inc, 
                      pr_inc=pr_inc, 
                      cycle=i)
        
        df_i, df_sub_i = _utandcost(df=df_i, 
                                    ut=ut, 
                                    cost=cost, 
                                    age_lb=age_lb, 
                                    age_ub=age_ub, 
                                    cycle=i,
                                    intervention=1,
                                    once_off_ind=once_off_ind, 
                                    once_off_st=once_off_st, 
                                    annual_ind=annual_ind, 
                                    annual_overall=annual_overall)
        df_sub_i['cycle'] = i
        df_sub_i['compint'] = 1
        tracking_i.append(df_sub_i)

    df_c = pd.concat(tracking_c, ignore_index=True)
    df_i = pd.concat(tracking_i, ignore_index=True)
    results_df = pd.concat([df_c, df_i], ignore_index=True)

    if discounting!=0:
        dc = discounting/100
        dc_values = ['yll', 'qaly', 'hccost', 'intcost', 'tcost']
        for var in dc_values:
            results_df[f'{var}'] = results_df[f'{var}']/((1+dc)**(results_df['cycle']-1))

    return results_df
