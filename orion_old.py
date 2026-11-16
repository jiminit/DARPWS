import pandas as pd
import numpy as np
import time
import warnings
from pandas.errors import PerformanceWarning
import plotly.express as px
import plotly.io as pio
import json
import plotly.utils
import plotly.graph_objects as go

def _events(df, tp_lt):

    df = pd.merge(df, tp_lt, on=['age', 'sex', 'sq', 'hstate'], how='inner')

    #Define outcomes
    outcomes = ['mi', 'hf', 'st', 'pd', 'eskd', 'hypo', 'hype', 'cvdeath', 'redeath', 'nondeath', 'nil']
    event_cols = [f'{oc}_event' for oc in outcomes]
    
    #Outcomes
    for oc in outcomes:
        df[f'{oc}_event'] = df['count'] * df[f'tp_{oc}']

    #Drop transition probabilities
    tp_cols = [col for col in df.columns if col.startswith('tp_')]
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

def _newdm(df, pop, dm_inc, pr_inc, cycle, dm_rrr):
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

    # Adjust diabetes incidence based on user input
    df_sub['dm_tp']*=(1-(dm_rrr/100))

    #New diabetes
    df_sub['no_dm'] = df_sub['pop'] - df_sub['new_count']
    df_sub['new_dm'] = df_sub['no_dm'] * df_sub['dm_tp']

    #Apportion to health states
    df_sub = pd.merge(pr_inc, df_sub, on=['age', 'sex', 'sq'], how='left')
    df_sub['total'] = df_sub.groupby(['age', 'sex', 'sq'])['pr'].transform('sum')
    df_sub['case'] = df_sub['new_dm'] * df_sub['pr'] / df_sub['total']

    df_sub.loc[df_sub['hstate']!=1, 'no_dm'] = 0

    #Final new case dataset
    df_sub = df_sub[['age', 'sex', 'sq', 'hstate', 'case', 'no_dm']]

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

def _cycle(df, tp_lt, transition_maps, death_transitions, pop, dm_inc, pr_inc, cycle, dm_rrr):
    df = _events(df=df, 
                            tp_lt=tp_lt)
    
    df = _apply_markov_transitions(df=df, 
                                        transition_maps=transition_maps, 
                                        death_transitions=death_transitions)
    
    df = _newdm(df=df, 
                    pop=pop, 
                    dm_inc=dm_inc, 
                    pr_inc=pr_inc, 
                    cycle=cycle,
                    dm_rrr=dm_rrr)
 

    df_sub = df.loc[df['hstate'] <= 32]
    df_sub = df_sub.groupby(['age', 'sex', 'sq'], as_index=False)[['count', 'new_count', 'case', 'no_dm']].sum()
    df_sub['cycle'] = cycle

    #Prepare dataframe for next cycle
    df['count2'] = df['new_count'] + df['case']
    df = df[['age', 'sex', 'sq', 'hstate', 'count2']]
    df = df.rename(columns={'count2': 'count'})

    return df_sub, df

def _utandcost(df, utg, age_lb, age_ub, once_off_st, annual_overall, discounting):
    
    df = df.sort_values(["age", "sex", "sq", "cycle"])
    df["no_dm_1"] = df.groupby(["age", "sex", "sq"])["no_dm"].shift(-1).ffill()

    # Last obs go up by 1.5% because that matches the trend in pop overall.
    df = df.sort_values(['age', 'sex', 'sq'])
    last_row_mask = ~df.duplicated(subset=['age', 'sex', 'sq'], keep='last')
    df.loc[last_row_mask, 'no_dm_1'] *= 1.015

    df['yll_nodm'] = (df['no_dm']+df['no_dm_1']+df['case'])/2
    df['yll_dm'] = (df['count']+df['new_count']+df['case'])/2
    df['yll'] = df['yll_nodm']+df['yll_dm']
    df = pd.merge(df, utg, on=['age', 'sex'], how='inner')
    df['qly_nodm'] = df['UT']*df['yll_nodm']
    df['qly_dm'] = df['UT']*df['yll_dm']*0.785
    df['qaly'] = df['qly_nodm']+df['qly_dm']
    df['hcc_dm'] = df['yll_dm']*5007.42

    intervention = 0
        #Intervention costs
    if intervention == 1:
        df['intcost'] = annual_overall
        df.loc[df['cycle']==1, 'intcost'] = df['intcost'] + once_off_st
    else:
        df['intcost'] = 0

    df['tcost'] = df['hcc_dm']+df['intcost']

    if discounting!=0:
        dc = discounting/100
        dc_values = ['yll_nodm', 'yll_dm', 'yll', 'qly_nodm', 'qly_dm', 'qaly', 'hcc_dm', 'intcost', 'tcost']
        for var in dc_values:
            df[f'{var}'] = df[f'{var}']/((1+dc)**(df['cycle']-1))

    df = df.loc[(df['age'] >= age_lb) & (df['age'] <= age_ub)]
    df = df.groupby(['sex', 'sq'], as_index=False)[['case', 'yll_nodm', 'yll_dm', 'yll', 'qly_nodm', 'qly_dm', 'qaly', 'hcc_dm', 'intcost', 'tcost']].sum()

    return df

def pax(age_lb, age_ub, dm_rrr, fc_t, ac_t, ncycles, discounting):
    
    #Load the initial data
    lt_init = pd.read_csv('lt_init_1.csv')
    tp_lt = pd.read_csv('tp_lt_1.csv')
    pop = pd.read_csv('pop_1.csv')
    dm_inc = pd.read_csv('dm_inc_rates_1.csv')
    pr_inc = pd.read_csv('pr_hstate_inc_1.csv')
    utg = pd.read_csv('utg.csv')

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

    df_c = lt_init
    df_i = lt_init
    tracking_c = []
    tracking_i = []
    for i in range(1,ncycles+1):

        df_sub_c, df_c = _cycle(df=df_c, 
                                tp_lt=tp_lt, 
                                transition_maps=transition_maps, 
                                death_transitions=death_transitions, 
                                pop=pop, 
                                dm_inc=dm_inc, 
                                pr_inc=pr_inc, 
                                cycle=i, 
                                dm_rrr=0)

        df_sub_i, df_i = _cycle(df=df_i, 
                                    tp_lt=tp_lt, 
                                    transition_maps=transition_maps, 
                                    death_transitions=death_transitions, 
                                    pop=pop, 
                                    dm_inc=dm_inc, 
                                    pr_inc=pr_inc, 
                                    cycle=i, 
                                    dm_rrr=dm_rrr)
        
        tracking_c.append(df_sub_c)
        tracking_i.append(df_sub_i)


    df_c = pd.concat(tracking_c, ignore_index=True)
    df_i = pd.concat(tracking_i, ignore_index=True)

    results_c = _utandcost(df=df_c, 
                            utg=utg, 
                            age_lb=age_lb, 
                            age_ub=age_ub, 
                            once_off_st=fc_t, 
                            annual_overall=ac_t,
                            discounting=discounting)
    results_c['compint'] = 0

    results_i = _utandcost(df=df_i, 
                            utg=utg, 
                            age_lb=age_lb, 
                            age_ub=age_ub, 
                            once_off_st=fc_t, 
                            annual_overall=ac_t,
                            discounting=discounting)
    results_i['compint'] = 1

    results_df = pd.concat([results_c, results_i], ignore_index=True)

    return results_df

