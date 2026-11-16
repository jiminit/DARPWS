
import pandas as pd
import numpy as np
import time

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

    df = df.copy()
    
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
    df['age'] = (df['age'] + 1).clip(upper=1000)
    df = df.groupby(['age', 'sex', 'sq', 'hstate'], as_index=False).sum()

    return df

def _newdm(df, pop, dm_inc, pr_inc):
    #Add incident diabetes

    #Keep alive
    df_sub = df.loc[df['hstate'] <= 32]

    #Lose health states/collapse
    df_sub = df_sub.groupby(['age', 'sex', 'sq'], as_index=False)['new_count'].sum()

    #Population for the cycle
    pop_1 = pop.loc[pop['cycle'] == 1]
    pop_1 = pop_1.drop(columns='cycle')

    #Combine
    df_sub = pd.merge(df_sub, pop_1, on=['age', 'sex', 'sq'], how='outer')
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
    
    return df

def _utandcost(df, ut, cost):
    df = pd.merge(df, ut, on=['age', 'sex', 'sq', 'hstate'], how='inner')
    df = pd.merge(df, cost, on=['age', 'sex', 'sq', 'hstate'], how='inner')
    df['qaly'] = (0.5*df['hstate_ut_pe']*(df['count'] + df['new_count'] + df['case']))+(df['hypo_event']*df['dis_hypo_pe'])+(df['hype_event']*df['dis_hype_pe'])
    df['cost'] = (0.5*df['cycle_cost']*(df['count'] + df['new_count'] + df['case']))+(df['hypo_event']*df['hypo_cost'])+(df['hype_event']*df['hype_cost'])
    df['death_event'] = df['cvdeath_event'] + df['redeath_event'] + df['nondeath_event']
    df_sub = df.groupby(['sex', 'sq'], as_index=False)[['count', 'mi_event', 'mi_event', 'hf_event', 'st_event', 'pd_event', 'eskd_event', 'hypo_event', 'hype_event', 'death_event', 'new_count', 'case', 'qaly', 'cost']].sum()
    
    df.loc[df['new_count'].isna(), 'new_count'] = 0
    df.loc[df['case'].isna(), 'case'] = 0

    df['count2'] = df['new_count'] + df['case']
    df = df[['age', 'sex', 'sq', 'hstate', 'count2']]
    df = df.rename(columns={'count2': 'count'})
    return df, df_sub

def allspark(a):

    #Load the initial data
    lt_init = pd.read_csv('lt_init.csv')
    tp_lt = pd.read_csv('tp_lt.csv')
    pop = pd.read_csv('pop.csv')
    dm_inc = pd.read_csv('dm_inc_rates.csv')
    pr_inc = pd.read_csv('pr_hstate_inc.csv')
    ut = pd.read_csv('utilities.csv')
    cost = pd.read_csv('costs.csv')

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
    df = lt_init
    tracking = []
    for i in range(1,2):
        print(i)
        df = _events(df=df, tp_lt=tp_lt)
        df = _apply_markov_transitions(df=df, transition_maps=transition_maps, death_transitions=death_transitions)
        df = _newdm(df=df, pop=pop, dm_inc=dm_inc, pr_inc=pr_inc)
        df, df_sub = _utandcost(df=df, ut=ut, cost=cost)
        df_sub['cycle'] = i
        tracking.append(df_sub)

    results_df = pd.concat(tracking, ignore_index=True)

    return results_df

##PICKUP: You have the loop now. From here, clean up what exists, then figure out how to present it. Dynamic graph interface to stratify by different variables and plot different variables. Plus overall tables that are dynamic as well. Also the loading screen page.
start_time = time.perf_counter()
a= None
results = allspark(a)
print(results)
end_time = time.perf_counter()
elapsed_time = end_time - start_time
print(f"Script executed in {elapsed_time:.2f} seconds")



# def allspark(dp_pop, dp_age_lb, dp_age_ub, dp_rrr,
#              dc_pop, dc_age_lb, dc_age_ub, dc_hf_rrr, dc_cv_rrr, 
#              dc_ck_rrr, dc_pn_rrr, fc_pp, fc_t, ac_pp, ac_t):
    
#     sc = 1
#     intn = 1
#     diff = 1

#     row = ['Incident diabetes',
#            'HF events',
#            'CVD events',
#            'CKD events',
#            'PN events',
#            'Deaths',
#            'QALYs',
#            'Healthcare costs (AUD)',
#            'ICER']

#     df = pd.DataFrame({
#         'row': row,
#         'SC': sc,
#         'intn': intn,
#         'diff': diff
#     })
    
#     return df

# float_fields = ['DP_pop', 
#                     'DP_age_lb', 
#                     'DP_age_ub', 
#                     'DP_RRR', 
#                     'DC_pop', 
#                     'DC_age_lb',
#                     'DC_age_ub',
#                     'DC_HF_RRR',
#                     'DC_CV_RRR',
#                     'DC_CK_RRR', 
#                     'DC_PN_RRR', 
#                     'FC_PP', 
#                     'FC_T',
#                     'AC_PP', 
#                     'AC_T']
# inputs = {f: None for f in float_fields}

# res1 = allspark(dp_pop=inputs['DP_pop'], 
#                     dp_age_lb=inputs['DP_age_lb'],
#                     dp_age_ub=inputs['DP_age_ub'], 
#                     dp_rrr=inputs['DP_RRR'],
#                     dc_pop=inputs['DC_pop'], 
#                     dc_age_lb=inputs['DC_age_lb'], 
#                     dc_age_ub=inputs['DC_age_ub'], 
#                     dc_hf_rrr=inputs['DC_HF_RRR'], 
#                     dc_cv_rrr=inputs['DC_CV_RRR'],
#                     dc_ck_rrr=inputs['DC_CK_RRR'], 
#                     dc_pn_rrr=inputs['DC_PN_RRR'], 
#                     fc_pp=inputs['FC_PP'], 
#                     fc_t=inputs['FC_T'], 
#                     ac_pp=inputs['AC_PP'], 
#                     ac_t=inputs['AC_T'])

#print(res1)


# import pandas as pd
# import numpy as np



# hstate_labels = {
#     1: "No complications",
#     2: "mi only",
#     3: "st only",
#     4: "pd only",
#     5: "hf only",
#     6: "eskd only",
#     7: "mi and st",
#     8: "mi and pd",
#     9: "mi and hf",
#     10: "mi and eskd",
#     11: "st and pd",
#     12: "st and hf",
#     13: "st and eskd",
#     14: "pd and hf",
#     15: "pd and eskd",
#     16: "hf and eskd",
#     17: "mi and st and pd",
#     18: "mi and st and hf",
#     19: "mi and st and eskd",
#     20: "st and pd and hf",
#     21: "st and hf and eskd",
#     22: "mi and pd and hf",
#     23: "mi and pd and eskd",
#     24: "mi and hf and eskd",
#     25: "pd and hf and eskd",
#     26: "st and pd and eskd",
#     27: "mi and st and pd and hf",
#     28: "mi and st and pd and eskd",
#     29: "mi and st and hf and eskd",
#     30: "mi and pd and hf and eskd",
#     31: "st and pd and hf and eskd",
#     32: "All complications",
#     33: "Death CV",
#     34: "Death renal",
#     35: "Death other"
# }
# # Creates a new labeled column while keeping the numeric code for calculations
# df['hstate_name'] = df['hstate'].map(hstate_labels)

# import pandas as pd
# import numpy as np

# def run_markov_simulation(baseline_df: pd.DataFrame, 
#                            n_cycles: int = 30, 
#                            outcomes: list = None) -> pd.DataFrame:
#     """
#     Runs a multi-year Markov simulation over n_cycles.
#     Returns a combined summary DataFrame across all cycles.
#     """
#     if outcomes is None:
#         outcomes = ['mi', 'hf', 'st', 'pd', 'eskd', 'hypo', 'hype', 'cvdeath', 'redeath', 'nondeath', 'nil']

#     # Work on a deep copy of baseline data
#     df = baseline_df.copy()
    
#     # Initialize initial state counts
#     df['count'] = df['baseline_count']
    





#     cycle_records = []

#     for cycle in range(1, n_cycles + 1):
#         # 1. Update age-dependent probabilities if age increments each cycle
#         # df['age'] = df['baseline_age'] + (cycle - 1)
#         # df = update_transition_probabilities(df) # Optional lookup function

#         # 2. Event Generation: calculate expected events for the current cycle
#         for oc in outcomes:
#             df[f'{oc}_event'] = df['count'] * df[f'tp_{oc}']

#         # 3. State Transitions: execute logic to populate df['new_count']
#         df = apply_markov_transitions(df)

#         # 4. Record Cycle Summary Metrics
#         # Aggregate population counts across states for this cycle
#         state_totals = df.groupby('hstate')['new_count'].sum().to_dict()
        
#         cycle_summary = {
#             'cycle': cycle,
#             'total_alive': df.loc[df['hstate'] <= 32, 'new_count'].sum(),
#             'total_deaths': df.loc[df['hstate'] >= 33, 'new_count'].sum(),
#         }
#         # Unpack state counts (e.g., state_1, state_2, ...) into columns
#         for state_id, total in state_totals.items():
#             cycle_summary[f'state_{state_id}'] = total

#         cycle_records.append(cycle_summary)

#         # 5. Rollover: update state counts for the next cycle
#         df['count'] = df['new_count'].copy()

#     # Combine all cycle records into a single summary DataFrame
#     results_df = pd.DataFrame(cycle_records)
#     return results_df



