import pandas as pd
import numpy as np
from pandas.errors import PerformanceWarning
import plotly.express as px
import plotly.io as pio
import json
import plotly.utils
import plotly.graph_objects as go


from orion import pax



def results_tables(df):
    
    df_sub = df.groupby(['sex', 'sq', 'compint'], as_index=False).sum()
    
    df_sub = df_sub.pivot(index=['sex','sq'], columns='compint', values=['mi_event', 'hf_event', 'st_event', 'pd_event', 'eskd_event', 'hypo_event', 'hype_event', 'death_event', 'yll', 'qaly', 'hccost', 'intcost', 'tcost']).reset_index()
    cols = ['mi_event', 'hf_event', 'st_event', 'pd_event', 'eskd_event', 'hypo_event', 'hype_event', 'death_event', 'yll', 'qaly', 'hccost', 'intcost', 'tcost']
    for col in cols:
        df_sub[(f'{col}', 2)] = df_sub[(f'{col}', 1)] - df_sub[(f'{col}', 0)]

    df_sub_sex = df_sub.drop(columns=['sq'], level=0).groupby(['sex'], as_index=False).sum()
    df_sub_sq = df_sub.drop(columns=['sex']).groupby(['sq'], as_index=False).sum()
    df_sub_ov = df_sub.drop(columns=['sex', 'sq']).sum().to_frame().T

    df_sub['icer', 2] = df_sub[('tcost', 2)]/df_sub[('qaly', 2)]
    df_sub = df_sub.set_index(['sex', 'sq'])
    df_sub = df_sub.stack(level=0, future_stack=True)
    df_sub = df_sub.reset_index()

    df_sub_sex['icer', 2] = df_sub_sex[('tcost', 2)]/df_sub_sex[('qaly', 2)]
    df_sub_sex = df_sub_sex.set_index(['sex'])
    df_sub_sex = df_sub_sex.stack(level=0, future_stack=True)
    df_sub_sex = df_sub_sex.reset_index()

    df_sub_sq['icer', 2] = df_sub_sq[('tcost', 2)]/df_sub_sq[('qaly', 2)]
    df_sub_sq = df_sub_sq.set_index(['sq'])
    df_sub_sq = df_sub_sq.stack(level=0, future_stack=True)
    df_sub_sq = df_sub_sq.reset_index()

    df_sub_ov['icer', 2] = df_sub_ov[('tcost', 2)]/df_sub_ov[('qaly', 2)]
    df_sub_ov = df_sub_ov.stack(level=0, future_stack=True)
    df_sub_ov = df_sub_ov.reset_index()
    df_sub_ov = df_sub_ov.drop(columns=['level_0'])

    df_sub = df_sub.rename(columns={'level_2': 'level_1'})

    dfs = [df_sub, df_sub_sex, df_sub_sq, df_sub_ov]
    for fd in dfs:
        for i in range(0,3):
            fd[i] = fd[i].map('{:,.0f}'.format)
            fd.loc[fd[i]=='nan', i] = ''

        fd.loc[fd['level_1']=='mi_event', 'level_1'] = 'Myocardial Infarctions'
        fd.loc[fd['level_1']=='hf_event', 'level_1'] = 'Hospitalisations for heart failure'
        fd.loc[fd['level_1']=='st_event', 'level_1'] = 'Strokes'
        fd.loc[fd['level_1']=='pd_event', 'level_1'] = 'Hospitalisation for peripheral disease'
        fd.loc[fd['level_1']=='eskd_event', 'level_1'] = 'End-stage kidney disease cases'
        fd.loc[fd['level_1']=='hypo_event', 'level_1'] = 'Hypoglycaemia hospitalisations'
        fd.loc[fd['level_1']=='hype_event', 'level_1'] = 'Hyperglycaemia hospitalisations'
        fd.loc[fd['level_1']=='death_event', 'level_1'] = 'Deaths'
        fd.loc[fd['level_1']=='yll', 'level_1'] = 'Years of life lived'
        fd.loc[fd['level_1']=='qaly', 'level_1'] = 'Quality-adjusted life years'
        fd.loc[fd['level_1']=='hccost', 'level_1'] = 'Healthcare costs (A$)'
        fd.loc[fd['level_1']=='intcost', 'level_1'] = 'Intervention costs (A$)'
        fd.loc[fd['level_1']=='tcost', 'level_1'] = 'Total costs (A$)'
        fd.loc[fd['level_1']=='icer', 'level_1'] = 'Incremental cost-effectiveness ratio (A$ per QALY)'

    df_sub = df_sub.rename(columns={'sex': 'Sex', 'sq': 'IRSD quintile', 'level_1': 'Outcomes', 0: 'Control', 1: 'Intervention', 2: 'Difference'})    
    df_sub_sex = df_sub_sex.rename(columns={'sex': 'Sex', 'level_1': 'Outcomes', 0: 'Control', 1: 'Intervention', 2: 'Difference'})
    df_sub_sq = df_sub_sq.rename(columns={'sq': 'IRSD quintile', 'level_1': 'Outcomes', 0: 'Control', 1: 'Intervention', 2: 'Difference'})
    df_sub_ov = df_sub_ov.rename(columns={'level_1': 'Outcomes', 0: 'Control', 1: 'Intervention', 2: 'Difference'})

    df_sub['Sex'] = df_sub['Sex'].map('{:,.0f}'.format)
    df_sub.loc[df_sub['Sex']=='1', 'Sex'] = 'Males'
    df_sub.loc[df_sub['Sex']=='2', 'Sex'] = 'Females'
    df_sub = pd.concat([df_sub[df_sub['Sex'] == 'Females'], df_sub[df_sub['Sex'] == 'Males']], ignore_index=True)

    df_sub_sex['Sex'] = df_sub_sex['Sex'].map('{:,.0f}'.format)
    df_sub_sex.loc[df_sub_sex['Sex']=='1', 'Sex'] = 'Males'
    df_sub_sex.loc[df_sub_sex['Sex']=='2', 'Sex'] = 'Females'        
    df_sub_sex = pd.concat([df_sub_sex[df_sub_sex['Sex'] == 'Females'], df_sub_sex[df_sub_sex['Sex'] == 'Males']], ignore_index=True)

    return df_sub, df_sub_sex, df_sub_sq, df_sub_ov

def restab(df):

    df_sub = df.pivot(index=['sex','sq'], columns='compint', values=['case', 'death', 'yll', 'qaly', 'hccost', 'intcost', 'tcost']).reset_index()

    cols = ['case', 'death', 'yll', 'qaly', 'hccost', 'intcost', 'tcost']
    for col in cols:
        df_sub[(f'{col}', 2)] = df_sub[(f'{col}', 1)] - df_sub[(f'{col}', 0)]

    df_sub_sex = df_sub.drop(columns=['sq'], level=0).groupby(['sex'], as_index=False).sum()
    df_sub_sq = df_sub.drop(columns=['sex']).groupby(['sq'], as_index=False).sum()
    df_sub_ov = df_sub.drop(columns=['sex', 'sq']).sum().to_frame().T

    df_sub['icer', 2] = df_sub[('tcost', 2)]/df_sub[('qaly', 2)]
    df_sub = df_sub.set_index(['sex', 'sq'])
    df_sub = df_sub.stack(level=0, future_stack=True)
    df_sub = df_sub.reset_index()

    df_sub_sex['icer', 2] = df_sub_sex[('tcost', 2)]/df_sub_sex[('qaly', 2)]
    df_sub_sex = df_sub_sex.set_index(['sex'])
    df_sub_sex = df_sub_sex.stack(level=0, future_stack=True)
    df_sub_sex = df_sub_sex.reset_index()

    df_sub_sq['icer', 2] = df_sub_sq[('tcost', 2)]/df_sub_sq[('qaly', 2)]
    df_sub_sq = df_sub_sq.set_index(['sq'])
    df_sub_sq = df_sub_sq.stack(level=0, future_stack=True)
    df_sub_sq = df_sub_sq.reset_index()

    df_sub_ov['icer', 2] = df_sub_ov[('tcost', 2)]/df_sub_ov[('qaly', 2)]
    df_sub_ov = df_sub_ov.stack(level=0, future_stack=True)
    df_sub_ov = df_sub_ov.reset_index()
    df_sub_ov = df_sub_ov.drop(columns=['level_0'])

    df_sub = df_sub.rename(columns={'level_2': 'level_1'})

    dfs = [df_sub, df_sub_sex, df_sub_sq, df_sub_ov]
    for fd in dfs:
        for i in range(0,3):
            fd[i] = fd[i].map('{:,.0f}'.format)
            fd.loc[fd[i]=='nan', i] = ''

        fd.loc[fd['level_1']=='case', 'level_1'] = 'Incident diabetes'
        fd.loc[fd['level_1']=='death', 'level_1'] = 'Deaths'
        fd.loc[fd['level_1']=='yll', 'level_1'] = 'Years of life lived'
        fd.loc[fd['level_1']=='qaly', 'level_1'] = 'Quality-adjusted life years'
        fd.loc[fd['level_1']=='hccost', 'level_1'] = 'Healthcare costs (A$)'
        fd.loc[fd['level_1']=='intcost', 'level_1'] = 'Intervention costs (A$)'
        fd.loc[fd['level_1']=='tcost', 'level_1'] = 'Total costs (A$)'
        fd.loc[fd['level_1']=='icer', 'level_1'] = 'Incremental cost-effectiveness ratio (A$ per QALY)'

    df_sub = df_sub.rename(columns={'sex': 'Sex', 'sq': 'IRSD quintile', 'level_1': 'Outcomes', 0: 'Control', 1: 'Intervention', 2: 'Difference'})    
    df_sub_sex = df_sub_sex.rename(columns={'sex': 'Sex', 'level_1': 'Outcomes', 0: 'Control', 1: 'Intervention', 2: 'Difference'})
    df_sub_sq = df_sub_sq.rename(columns={'sq': 'IRSD quintile', 'level_1': 'Outcomes', 0: 'Control', 1: 'Intervention', 2: 'Difference'})
    df_sub_ov = df_sub_ov.rename(columns={'level_1': 'Outcomes', 0: 'Control', 1: 'Intervention', 2: 'Difference'})

    df_sub['Sex'] = df_sub['Sex'].map('{:,.0f}'.format)
    df_sub.loc[df_sub['Sex']=='1', 'Sex'] = 'Males'
    df_sub.loc[df_sub['Sex']=='2', 'Sex'] = 'Females'
    df_sub = pd.concat([df_sub[df_sub['Sex'] == 'Females'], df_sub[df_sub['Sex'] == 'Males']], ignore_index=True)

    df_sub_sex['Sex'] = df_sub_sex['Sex'].map('{:,.0f}'.format)
    df_sub_sex.loc[df_sub_sex['Sex']=='1', 'Sex'] = 'Males'
    df_sub_sex.loc[df_sub_sex['Sex']=='2', 'Sex'] = 'Females'        
    df_sub_sex = pd.concat([df_sub_sex[df_sub_sex['Sex'] == 'Females'], df_sub_sex[df_sub_sex['Sex'] == 'Males']], ignore_index=True)

    return df_sub, df_sub_sex, df_sub_sq, df_sub_ov

def results_CEP_sexsq(df):
    df_sub = df.groupby(['sex', 'sq', 'compint'], as_index=False)[['qaly', 'tcost']].sum()

    df_sub = df_sub.sort_values(by=['sex', 'sq', 'compint'])
    df_sub['qly'] = df_sub.groupby(['sex', 'sq'])['qaly'].diff()
    df_sub['cst'] = df_sub.groupby(['sex', 'sq'])['tcost'].diff()

    df_sub = df_sub.loc[df_sub['compint']==1]

    df_sub['ICER'] = df_sub['cst']/df_sub['qly']

    df_sub.loc[df_sub['sex']==1, 'Sex'] = 'Male'
    df_sub.loc[df_sub['sex']==2, 'Sex'] = 'Female'

    fig = px.scatter(df_sub,
                    x="qly", 
                    y="cst", 
                    custom_data=['Sex', 'sq', 'ICER'],
                    color=df_sub['sq'].astype(str),
                    color_discrete_sequence=px.colors.qualitative.Dark24,
                    symbol='Sex',
                    symbol_map={'Female': 'circle', 'Male': 'square'},
                    title="By sex and IRSD"
                    )

    fig.update_layout(
                    xaxis_title="QALYs gained",
                    yaxis_title="Incremental healthcare costs",
                    font=dict(family="sans-serif", size=18, color="black"),
                    plot_bgcolor='white',
                    height=450,
                    margin=dict(t=50, b=50, l=50, r=50),
                    title_font=dict(size=18),
                    legend_title_text="IRSD quintile, sex"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>Sex:</b> %{customdata[0]}<br>" +
            "<b>IRSD quintile:</b> %{customdata[1]}<br>" +
            "<b>QALYs gained:</b> %{x:.0f}<br>" +
            "<b>Incremental costs:</b> $%{y:,.0f}<br>" +
            "<b>ICER:</b> %{customdata[2]:,.0f}"
            "<extra></extra>"
        )
    )



    fig.update_xaxes(
    tickformat=',d',
    zeroline=True, 
    zerolinecolor='black', 
    zerolinewidth=2,
    showgrid=True, 
    gridcolor='#e5e5e5',
    showline=True, 
    linecolor='black',
    )

    fig.update_yaxes(
    tickformat='$,.0f',
    zeroline=True, 
    zerolinecolor='black', 
    zerolinewidth=2,
    gridcolor='#e5e5e5',
    showline=True, 
    linecolor='black',
    )
    maxQLY = df_sub['qly'].max()

    fig.add_trace(go.Scatter(
    x=[0, maxQLY],
    y=[0, maxQLY * 50000],
    mode='lines',
    name='WTP ($50k/QALY)',
    line=dict(color='black', width=2)
    ))

    return fig

def results_CEP_sq(df):
    df_sub = df.groupby(['sq', 'compint'], as_index=False)[['qaly', 'tcost']].sum()

    df_sub = df_sub.sort_values(by=['sq', 'compint'])
    df_sub['qly'] = df_sub.groupby(['sq'])['qaly'].diff()
    df_sub['cst'] = df_sub.groupby(['sq'])['tcost'].diff()

    df_sub = df_sub.loc[df_sub['compint']==1]

    df_sub['ICER'] = df_sub['cst']/df_sub['qly']

    fig = px.scatter(df_sub,
                    x="qly", 
                    y="cst", 
                    custom_data=['sq', 'ICER'],
                    color=df_sub['sq'].astype(str),
                    color_discrete_sequence=px.colors.qualitative.Dark24,
                    title="By IRSD"
                    )

    fig.update_layout(
                    xaxis_title="QALYs gained",
                    yaxis_title="Incremental healthcare costs",
                    font=dict(family="sans-serif", size=18, color="black"),
                    plot_bgcolor='white',
                    height=450,
                    margin=dict(t=50, b=50, l=50, r=50),
                    title_font=dict(size=18),
                    legend_title_text="IRSD quintile"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>IRSD quintile:</b> %{customdata[0]}<br>" +
            "<b>QALYs gained:</b> %{x:.0f}<br>" +
            "<b>Incremental costs:</b> $%{y:,.0f}<br>" +
            "<b>ICER:</b> %{customdata[1]:,.0f}"
            "<extra></extra>"
        )
    )




    fig.update_xaxes(
    tickformat=',d',
    zeroline=True, 
    zerolinecolor='black', 
    zerolinewidth=2,
    showgrid=True, 
    gridcolor='#e5e5e5',
    showline=True, 
    linecolor='black',
    )

    fig.update_yaxes(
    tickformat='$,.0f',
    zeroline=True, 
    zerolinecolor='black', 
    zerolinewidth=2,
    gridcolor='#e5e5e5',
    showline=True, 
    linecolor='black',
    )
    maxQLY = df_sub['qly'].max()

    fig.add_trace(go.Scatter(
    x=[0, maxQLY],
    y=[0, maxQLY * 50000],
    mode='lines',
    name='WTP ($50k/QALY)',
    line=dict(color='black', width=2)
    ))

    return fig

def results_CEP_sex(df):
    df_sub = df.groupby(['sex', 'compint'], as_index=False)[['qaly', 'tcost']].sum()

    df_sub = df_sub.sort_values(by=['sex', 'compint'])
    df_sub['qly'] = df_sub.groupby(['sex'])['qaly'].diff()
    df_sub['cst'] = df_sub.groupby(['sex'])['tcost'].diff()

    df_sub = df_sub.loc[df_sub['compint']==1]

    df_sub['ICER'] = df_sub['cst']/df_sub['qly']

    df_sub.loc[df_sub['sex']==1, 'Sex'] = 'Male'
    df_sub.loc[df_sub['sex']==2, 'Sex'] = 'Female'

    fig = px.scatter(df_sub,
                    x="qly", 
                    y="cst", 
                    custom_data=['Sex', 'ICER'],
                    symbol='Sex',
                    symbol_map={'Female': 'circle', 'Male': 'square'},
                    title="By sex"
                    )

    fig.update_layout(
                    xaxis_title="QALYs gained",
                    yaxis_title="Incremental healthcare costs",
                    font=dict(family="sans-serif", size=18, color="black"),
                    plot_bgcolor='white',
                    height=450,
                    margin=dict(t=50, b=50, l=50, r=50),
                    title_font=dict(size=18),
                    legend_title_text="Sex"
    )

    fig.update_traces(
        hovertemplate=(
            "<b>Sex:</b> %{customdata[0]}<br>" +
            "<b>QALYs gained:</b> %{x:.0f}<br>" +
            "<b>Incremental costs:</b> $%{y:,.0f}<br>" +
            "<b>ICER:</b> %{customdata[1]:,.0f}"
            "<extra></extra>"
        )
    )



    fig.update_xaxes(
    tickformat=',d',
    zeroline=True, 
    zerolinecolor='black', 
    zerolinewidth=2,
    showgrid=True, 
    gridcolor='#e5e5e5',
    showline=True, 
    linecolor='black',
    )

    fig.update_yaxes(
    tickformat='$,.0f',
    zeroline=True, 
    zerolinecolor='black', 
    zerolinewidth=2,
    gridcolor='#e5e5e5',
    showline=True, 
    linecolor='black',
    )
    maxQLY = df_sub['qly'].max()

    fig.add_trace(go.Scatter(
    x=[0, maxQLY],
    y=[0, maxQLY * 50000],
    mode='lines',
    name='WTP ($50k/QALY)',
    line=dict(color='black', width=2)
    ))

    return fig

def results_CEP(df):
    df_sub = df.groupby(['compint'], as_index=False)[['qaly', 'tcost']].sum()
    df_sub = df_sub.sort_values(by=['compint'])
    df_sub['qly'] = df_sub['qaly'].diff()
    df_sub['cst'] = df_sub['tcost'].diff()
    df_sub = df_sub.loc[df_sub['compint']==1]
    df_sub['ICER'] = df_sub['cst']/df_sub['qly']

    fig = px.scatter(df_sub,
                    x="qly", 
                    y="cst", 
                    custom_data=['ICER'],
                    title="Overall"
                    )

    fig.update_layout(
                    xaxis_title="QALYs gained",
                    yaxis_title="Incremental healthcare costs",
                    font=dict(family="sans-serif", size=18, color="black"),
                    plot_bgcolor='white',
                    height=450,
                    margin=dict(t=50, b=50, l=50, r=50),
                    title_font=dict(size=18),
    )

    fig.update_traces(
        hovertemplate=(
            "<b>QALYs gained:</b> %{x:.0f}<br>" +
            "<b>Incremental costs:</b> $%{y:,.0f}<br>" +
            "<b>ICER:</b> %{customdata[0]:,.0f}"
            "<extra></extra>"
        )
    )

    
    maxQLY = df_sub['qly'].max()

    fig.update_xaxes(
    tickformat=',d',
    zeroline=True, 
    zerolinecolor='black', 
    zerolinewidth=2,
    showgrid=True, 
    gridcolor='#e5e5e5',
    showline=True, 
    linecolor='black',
    )

    fig.update_yaxes(
    tickformat='$,.0f',
    zeroline=True, 
    zerolinecolor='black', 
    zerolinewidth=2,
    gridcolor='#e5e5e5',
    showline=True, 
    linecolor='black',
    )

    fig.add_trace(go.Scatter(
    x=[0, maxQLY],
    y=[0, maxQLY * 50000],
    mode='lines',
    name='WTP ($50k/QALY)',
    line=dict(color='black', width=2)
    ))

    return fig

