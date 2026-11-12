
# User guide (Hyperlink github repo)
# Add: A1c reduction stuff


import pandas as pd
import numpy as np
import os
import time
import plotly.express as px
import plotly.io as pio
import csv
import io
import zipfile

from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
from orion import pax
from cybertronian import cybertronian
from prime import results_tables, restab, results_CEP_sexsq, results_CEP_sq, results_CEP_sex, results_CEP


app = Flask(__name__)
app.secret_key = "412351453dbcugahytve3825" 


@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/results', methods=['POST'])
def calculate():
    session['user_data'] = request.form
    saved_inputs = session.get('user_data', {})
    user_id = session.get('_id', 'guest')[:8]

    def safe_float(value):
        try:
            return float(value) if value else 0
        except (ValueError, TypeError):
            return None

    float_fields = ['model',
                    'DP_age_lb',
                    'DP_age_ub',
                    'dp_rrr',
                    'dp_fc_t',
                    'dp_ac_t',
                    'dp_cycles',
                    'DC_age_lb',
                    'DC_age_ub',
                    'a1c_r',
                    'mi_rrr',
                    'hf_rrr',
                    'st_rrr', 
                    'pd_rrr', 
                    'eskd_rrr', 
                    'hypo_rrr',
                    'hype_rrr', 
                    'cvdeath_rrr',
                    'redeath_rrr',
                    'fc_pp', 
                    'fc_t',
                    'ac_pp',
                    'ac_t',
                    'cycles']
    inputs = {f: safe_float(request.form.get(f)) for f in float_fields}

    try:
        if (inputs['DC_age_lb'] > inputs['DC_age_ub']):
            return "Error: Lower bounds of age must be less than upper bounds of age.", 400
        if (inputs['DP_age_lb'] > inputs['DP_age_ub']):
            return "Error: Lower bounds of age must be less than upper bounds of age.", 400
    except ValueError:
        return "Please enter valid numbers.", 400

    if inputs['DP_age_lb'] == 0:
        inputs['DP_age_lb'] = 0

    if inputs['DP_age_ub'] == 0:
        inputs['DP_age_ub'] = 100

    if inputs['DC_age_lb'] == 0:
        inputs['DC_age_lb'] = 20

    if inputs['DC_age_ub'] == 0:
        inputs['DC_age_ub'] = 100
    
    if inputs['dp_cycles'] == 0:
        inputs['dp_cycles'] = 10
    inputs['dp_cycles'] = int(inputs['dp_cycles'])

    if inputs['cycles'] == 0:
        inputs['cycles'] = 10
    inputs['cycles'] = int(inputs['cycles'])

    disc = request.form.get('dp_discounting')
    if disc == '':
        disc = 5
    else:
        disc = float(disc)

    inputs['dp_discounting'] = disc

    disc = request.form.get('discounting')
    if disc == '':
        disc = 5
    else:
        disc = float(disc)

    inputs['discounting'] = disc

    if inputs['model'] == 0:
        df_c= pax(ncycles=inputs['dp_cycles'], 
                  dm_rrr=0, 
                  compint=0, 
                  annual_overall=0, 
                  once_off_st=0, 
                  age_lb=inputs['DP_age_lb'], 
                  age_ub=inputs['DP_age_ub'], 
                  discounting=inputs['dp_discounting'])
        df_i= pax(ncycles=inputs['dp_cycles'], 
                          dm_rrr=inputs['dp_rrr'], 
                          compint=1, 
                          annual_overall=inputs['dp_ac_t'], 
                          once_off_st=inputs['dp_fc_t'], 
                          age_lb=inputs['DP_age_lb'], 
                          age_ub=inputs['DP_age_ub'], 
                          discounting=inputs['dp_discounting'])
        results = pd.concat([df_c, df_i], ignore_index=True)
        tab1, tab2, tab3, tab4 = restab(results)
        fig1 = results_CEP(results)
        fig2 = results_CEP_sex(results)
        fig3 = results_CEP_sq(results)
        fig4 = results_CEP_sexsq(results)


    if inputs['model'] == 1:
        results = cybertronian(age_lb=inputs['DC_age_lb'], 
                               age_ub=inputs['DC_age_ub'],
                               a1c_r=inputs['a1c_r'],
                               mi_rrr=inputs['mi_rrr'], 
                               hf_rrr=inputs['hf_rrr'], 
                               st_rrr=inputs['st_rrr'], 
                               pd_rrr=inputs['pd_rrr'], 
                               eskd_rrr=inputs['eskd_rrr'], 
                               hypo_rrr=inputs['hypo_rrr'], 
                               hype_rrr=inputs['hype_rrr'], 
                               cvdeath_rrr=inputs['cvdeath_rrr'], 
                               redeath_rrr=inputs['redeath_rrr'], 
                               fc_pp=inputs['fc_pp'], 
                               fc_t=inputs['fc_t'], 
                               ac_pp=inputs['ac_pp'], 
                               ac_t=inputs['ac_t'], 
                               ncycles=inputs['cycles'], 
                               discounting=inputs['discounting'])
        tab1, tab2, tab3, tab4 = results_tables(results)
        fig1 = results_CEP(results)
        fig2 = results_CEP_sex(results)
        fig3 = results_CEP_sq(results)
        fig4 = results_CEP_sexsq(results)




    tables = {
        'Overall': {
            'title': 'Overall',
            'headers': tab4.columns.tolist(),
            'align': ['left', 'right', 'right', 'right'],
            'bold': [True, False, False, False],
            'data': tab4.values.tolist()
                },
        'By sex': {
            'title': 'By sex',
            'headers': tab2.columns.tolist(),
            'align': ['left', 'left', 'right', 'right', 'right'],
            'bold': [True, True, False, False, False],
            'data': tab2.values.tolist()
                },
        'By IRSD': {
            'title': 'By IRSD',
            'headers': tab3.columns.tolist(),
            'align': ['left', 'left', 'right', 'right', 'right'],
            'bold': [True, True, False, False, False],
            'data': tab3.values.tolist()
                },
        'By sex and IRSD': {
            'title': 'By sex and IRSD',
            'headers': tab1.columns.tolist(),
            'align': ['left', 'left', 'left', 'right', 'right', 'right'],
            'bold': [True, True, True, False, False, False],
            'data': tab1.values.tolist()
                },
            }
        

       
    graph_json1 = pio.to_json(fig1)
    graph_json2 = pio.to_json(fig2)
    graph_json3 = pio.to_json(fig3)
    graph_json4 = pio.to_json(fig4)

    session['user_inputs'] = inputs
    session['tables'] = tables

    return render_template('results.html', tables=tables, data=saved_inputs, graphJSON1=graph_json1, graphJSON2=graph_json2, graphJSON3=graph_json3, graphJSON4=graph_json4, inputs=inputs)


@app.route('/download_tables', methods=['POST'])
def download_tables():
    tables = session.get('tables', {})
    selected_keys = request.form.getlist('selected_tables')

    if not selected_keys:
        return "Please select at least one table to download.", 400

    if len(selected_keys) == 1:
        key = selected_keys[0]
        table_info = tables.get(key, [])

        headers = table_info.get('headers', [])
        data = table_info.get('data', [])

        output = io.StringIO()
        writer = csv.writer(output)

        if headers:
            writer.writerow(headers)
        if data:
            writer.writerows(data)
      
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={key}.csv"}
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
        for key in selected_keys:
            if key in tables:
                table_info = tables[key]
                headers = table_info.get('headers', [])
                data = table_info.get('data', [])

                csv_output = io.StringIO()
                writer = csv.writer(csv_output)
                if headers:
                    writer.writerow(headers)
                if data:
                    writer.writerows(data)
                
                zip_file.writestr(f"{key}.csv", csv_output.getvalue())

    zip_buffer.seek(0)
    return Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment;filename=selected_tables.zip"}
    )

@app.route('/restart')
def restart():
    session.clear() 
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
