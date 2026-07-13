import openpyxl
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

materials = pd.read_csv("../data/processed/materials_detail.csv")

file_names = materials['Source File'].unique().tolist()

#pd.DataFrame({"file_name": file_names}).to_csv("./data/processed/file_names.csv", index=False)

file_convs = pd.read_csv("./data/processed/file_names.csv")

material_names = materials['Material'].unique().tolist()
copper_names = [name for name in material_names if ('CU' in name.upper() or 'COPPER' in name.upper())]

copper_materials = materials[materials['Material'].isin(copper_names)]
df = copper_materials[['Source File', 'Width (in)', 'Height (in)']]

df = df.groupby(['Source File', 'Height (in)']).sum().reset_index()

# Project Name
file_to_proj = dict(zip(file_convs['file_name'], file_convs['Project']))

# Switchboard Name
file_to_board = dict(zip(file_convs['file_name'], file_convs['Switchboard']))

# # Sections
file_to_numsections = dict(zip(file_convs['file_name'], file_convs['# Sections']))

# Amperage
file_to_amperage = dict(zip(file_convs['file_name'], file_convs['Amperage']))

# Map the values to the DataFrame
df['Project'] = df['Source File'].map(file_to_proj)
df['Switchboard'] = df['Source File'].map(file_to_board)
df['# Sections'] = df['Source File'].map(file_to_numsections)
df['Amperage'] = df['Source File'].map(file_to_amperage).astype('string')

df = df[['Project', 'Switchboard', '# Sections', 'Amperage', 'Height (in)', 'Width (in)']]
df = df.groupby(['Project', 'Switchboard', '# Sections', 'Amperage', 'Height (in)']).sum().reset_index()

# This data point is the oldest and a big outlier, so we are removing it from the analysis.
df.drop(df[(df['Project']=='25-132') & (df['Switchboard']=='HSW MDP')].index, inplace=True)

st.header("Copper Usage Analysis")

st.subheader("List of Boards Included in This Report")
# Only include boards with more than 1 section, since boards with 1 section do not include any horizontal bussing and would skew the data.
temp_df = df[df['# Sections'] > 1]
st.write(temp_df[['Project', 'Switchboard']].groupby(['Project', 'Switchboard']).sum().reset_index())

def copper_refactored(height, length):
    # 3" to be reclassified as 2" copper 
    if height == 3:
        return length * 1.5
    # 5" to be reclassified as 4" copper 
    if height == 5:
        return length * 1.25
    # 6" to be reclassified as 4" copper 
    if height == 6:
        return length * 1.5
    return length

height_map = {
    2: 2,
    3: 2,
    4: 4,
    5: 4,
    6: 4
}

df['Refactored Height (in)'] = df['Height (in)'].map(height_map)
df['Refactored Length (in)'] = df.apply(lambda row: copper_refactored(row['Height (in)'], row['Width (in)']), axis=1)

df = df[['Project', 'Switchboard', '# Sections', 'Amperage', 'Refactored Height (in)', 'Refactored Length (in)']]
df = df.groupby(['Project', 'Switchboard', '# Sections', 'Amperage', 'Refactored Height (in)']).sum().reset_index()

def feet_per_section(row):
    if row['# Sections'] == 0:
        return 0
    return row['Refactored Length (in)'] / row['# Sections'] / 12
    
df['Feet per Section'] = df.apply(feet_per_section, axis=1)

st.write("This report only includes boards with more than 1 section. Single section boards would skew the data since they do not include any horizontal bussing, and we don't have enough data to do a meaningful analysis just on those boards.")


st.space(30)


st.subheader("Phase Conductor (4\"-6\") Copper Usage per Section")

st.write("For all of the data in this section, the copper heights are all refactored to 4\". For example, \n - 100 feet of 5\" copper is reclassified as 125 feet of 4\" copper, \n - 100 feet of 6\" copper is reclassified as 150 feet of 4\" copper.")

phasecondcu_gt1section_df = df[(df['Refactored Height (in)'] == 4) & (df['# Sections'] > 1)]

order = [str(i)+"a" for i in sorted(df['Amperage'].astype(int).unique().tolist())]
phasecondcu_gt1section_df['Amperage String'] = phasecondcu_gt1section_df['Amperage'].astype(int).astype(str) + "a"

fig = px.box(
    phasecondcu_gt1section_df,
    x='Amperage String', 
    y='Feet per Section', 
    category_orders={'Amperage String': order},
    color='Amperage String', 
    title="Length of 4\" Copper Used for Boards With More Than 1 Section",
    points = 'all', 
    hover_data=['Project', 'Switchboard'],
)
fig = fig.update_layout(showlegend=False)
fig = fig.update_xaxes(title_text='Amperage', tickangle=0)
st.plotly_chart(fig)

phasecondcu_gt1section_df = phasecondcu_gt1section_df.groupby(['Amperage']).agg({'Feet per Section': 'mean'}).reset_index()
phasecondcu_gt1section_df = phasecondcu_gt1section_df.rename(columns={'Feet per Section': 'Average Feet per Section'})
phasecondcu_gt1section_df['Amperage'] = phasecondcu_gt1section_df['Amperage'].astype(int).round(0)
phasecondcu_gt1section_df['Average Feet per Section with 20% Scrap'] = phasecondcu_gt1section_df['Average Feet per Section'] * 1.2
qty_sold = {
    1200: 80,
    1600: 80,
    2000: 80,
    2500: 80,
    3000: 80,
    4000: 160
}
phasecondcu_gt1section_df['Feet Quoted per Section'] = phasecondcu_gt1section_df['Amperage'].map(qty_sold)

st.write("Below shows the average length of 4\" copper used for each amperage in dark blue, along with the average length assuming 20% scrap in light blue. The red line then represents the quantity of copper we are using to calculate our costs going into our quotes. **The red line should be at or above the light blue line**.")

fig = px.line(
    phasecondcu_gt1section_df, 
    x='Amperage', 
    y=['Average Feet per Section', 'Average Feet per Section with 20% Scrap', 'Feet Quoted per Section'], 
    title="Average Length of 4\" Copper Used for Boards With More Than 1 Section (with 20% Scrap)", 
    markers=True)

fig.update_yaxes(title_text='Feet per Section')

st.plotly_chart(fig)


st.space(30)


st.subheader("Ground and Bonding Conductor (2\"-3\") Copper Usage per Section")

st.write("For all of the data in this section, 3\" copper is refactored to 2\". For example, \n - 100 feet of 3\" copper is reclassified as 150 feet of 2\" copper.")

groundcondcu_gt1section_df = df[(df['Refactored Height (in)'] == 2) & (df['# Sections'] > 1)]

order = [str(i)+"a" for i in sorted(df['Amperage'].astype(int).unique().tolist())]
groundcondcu_gt1section_df['Amperage String'] = groundcondcu_gt1section_df['Amperage'].astype(int).astype(str) + "a"
groundcondcu_gt1section_df.drop(groundcondcu_gt1section_df[(groundcondcu_gt1section_df['Project']=='26-0507') & (groundcondcu_gt1section_df['Switchboard']=='SWB1A')].index, inplace=True)

fig = px.box(
    groundcondcu_gt1section_df,
    x='Amperage String', 
    y='Feet per Section', 
    category_orders={'Amperage String': order},
    color='Amperage String', 
    title="Length of 2\" Copper Used for Boards With More Than 1 Section",
    points = 'all', 
    hover_data=['Project', 'Switchboard'],
)
fig = fig.update_layout(showlegend=False)
fig = fig.update_xaxes(title_text='Amperage', tickangle=0)
st.plotly_chart(fig)

groundcondcu_gt1section_df = groundcondcu_gt1section_df.groupby(['Amperage']).agg({'Feet per Section': 'mean'}).reset_index()
groundcondcu_gt1section_df = groundcondcu_gt1section_df.rename(columns={'Feet per Section': 'Average Feet per Section'})
groundcondcu_gt1section_df['Amperage'] = groundcondcu_gt1section_df['Amperage'].astype(int).round(0)
groundcondcu_gt1section_df['Average Feet per Section with 20% Scrap'] = groundcondcu_gt1section_df['Average Feet per Section'] * 1.2
qty_sold = {
    1200: 20,
    1600: 20,
    2000: 20,
    2500: 20,
    3000: 20,
    4000: 40
}
groundcondcu_gt1section_df['Feet Quoted per Section'] = groundcondcu_gt1section_df['Amperage'].map(qty_sold)

st.write("Below shows the average length of 2\" copper used for each amperage in dark blue, along with the average length assuming 20% scrap in light blue. The red line then represents the quantity of copper we are using to calculate our costs going into our quotes. **The red line should be at or above the light blue line**.")

fig = px.line(
    groundcondcu_gt1section_df, 
    x='Amperage', 
    y=['Average Feet per Section', 'Average Feet per Section with 20% Scrap', 'Feet Quoted per Section'], 
    title="Average Length of 2\" Copper Used for Boards With More Than 1 Section (with 20% Scrap)", 
    markers=True)

fig.update_yaxes(title_text='Feet per Section')

st.plotly_chart(fig)


st.space(30)


st.subheader("Copper Over/Undercharge Analysis")

st.write("We are now assuming that our 'actual' usage is the *Average Feet per Section with 20% Scrap* data calculated and visualized above in light blue. The above shows that we are undercharging for the phase conductor (4\") copper on 2500a+ boards, and we are overcharging for all other copper. This can be visualized in the below chart.")


phasecondcu_gt1section_df['Footage Delta'] = phasecondcu_gt1section_df['Feet Quoted per Section'] - phasecondcu_gt1section_df['Average Feet per Section with 20% Scrap']
phasecondcu_gt1section_df['Cost Delta'] = phasecondcu_gt1section_df['Footage Delta'] * 40
phasecondcu_gt1section_df["Price Delta"] = phasecondcu_gt1section_df['Cost Delta'] * 1.4
phasecond_df = phasecondcu_gt1section_df.rename(columns={'Average Feet per Section': 'Phase Average Feet per Section', 'Feet Quoted per Section': 'Phase Feet Quoted per Section', 'Average Feet per Section with 20% Scrap': 'Phase Average Feet per Section with 20% Scrap', 'Footage Delta': 'Phase Footage Delta', 'Cost Delta': 'Phase Cost Delta', 'Price Delta': 'Phase Price Delta'})

groundcondcu_gt1section_df['Footage Delta'] = groundcondcu_gt1section_df['Feet Quoted per Section'] - groundcondcu_gt1section_df['Average Feet per Section with 20% Scrap']
groundcondcu_gt1section_df['Cost Delta'] = groundcondcu_gt1section_df['Footage Delta'] * 20
groundcondcu_gt1section_df["Price Delta"] = groundcondcu_gt1section_df['Cost Delta'] * 1.4
groundcond_df = groundcondcu_gt1section_df.rename(columns={'Average Feet per Section': 'Ground Average Feet per Section', 'Feet Quoted per Section': 'Ground Feet Quoted per Section', 'Average Feet per Section with 20% Scrap': 'Ground Average Feet per Section with 20% Scrap', 'Footage Delta': 'Ground Footage Delta', 'Cost Delta': 'Ground Cost Delta', 'Price Delta': 'Ground Price Delta'})

deltas_df = pd.merge(phasecond_df, groundcond_df, on='Amperage', how='outer')
deltas_df['Total Cost Delta'] = deltas_df['Phase Cost Delta'] + deltas_df['Ground Cost Delta']
deltas_df['Total Price Delta'] = deltas_df['Phase Price Delta'] + deltas_df['Ground Price Delta']



order = [str(i)+"a" for i in sorted(deltas_df['Amperage'].astype(int).unique().tolist())]
deltas_df['Amperage String'] = deltas_df['Amperage'].astype(int).astype(str) + "a"
deltas_df['Over/Undercharge'] = deltas_df['Total Price Delta'].apply(lambda x: 'Undercharge' if x < 0 else 'Overcharge')
color_map = {'Undercharge': 'red', 'Overcharge': 'green'}

fig = go.Figure(
    layout=dict(
    title="Delta Between Quoted and 'Actual' Copper Footage per Section by Amperage",
    xaxis=dict(title="Amperage"),
    yaxis=dict(title="Footage per Section Delta (ft)", ticksuffix="ft")
    )
)

fig.add_trace(go.Bar(
    x=deltas_df['Amperage String'],
    y=deltas_df['Phase Footage Delta'],
    name='4\" Copper Delta',
    width = 0.6,
    text=[f"{v:,.0f}ft" for v in deltas_df['Phase Footage Delta']],  
))

fig.add_trace(go.Bar(
    x=deltas_df['Amperage String'],
    y=deltas_df['Ground Footage Delta'],
    name='2\" Copper Delta',
    width = 0.3,
    text=[f"{v:,.0f}ft" for v in deltas_df['Ground Footage Delta']],     
))

st.plotly_chart(fig)

#st.write(deltas_df)
st.write("We can then calculate the delta between what we are charging and what we should be charging, (using our standard markup percentage and the 20/foot and 40/foot costs for 2\" and 4\" copper, respectively).")

fig = px.bar(deltas_df, 
    x='Amperage String',
    y='Total Price Delta', 
    text=[f"${v:,.2f}" for v in deltas_df['Total Price Delta']],
    category_orders={'Amperage String': order},
    color='Over/Undercharge',
    color_discrete_map=color_map,
    title="Current Amount of Over/Undercharge for Copper per Section by Amperage", 
    barmode='stack'
)

fig.update_xaxes(title_text='Amperage', tickangle=0)
fig.update_yaxes(title_text='Over/Undercharge ($)', tickprefix="$")


st.plotly_chart(fig)