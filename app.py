import base64
from io import BytesIO
import pandas as pd
import streamlit as st
import altair as alt

# Function to load data
@st.cache_data
def load_data(file):
    try:
        if file.type == 'text/csv':
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

@st.cache_data
def get_unique_values(df, column):
    return sorted(df[column].astype(str).unique())

def get_user_inputs(df, file):
    st.sidebar.subheader(f"Settings for {file.name}")
    all_dates = get_unique_values(df, 'Local Date')
    select_all_dates = st.sidebar.checkbox(f'Select All Dates', value=True, key=f"{file.name}_all_dates")
    local_dates = all_dates if select_all_dates else st.sidebar.multiselect(f'Select Local Date(s)', all_dates, key=f"{file.name}_dates")

    location_names = st.sidebar.multiselect(f'Select Location Name(s)', get_unique_values(df, 'Location Name'), key=f"{file.name}_locations")
    ssid = st.sidebar.multiselect(f'Select SSID(s)', get_unique_values(df, 'SSID'), key=f"{file.name}_ssid")

    location_type_options = get_unique_values(df, 'Location Type')
    default_location_type = "network" if "network" in location_type_options else location_type_options[0]
    location_type = st.sidebar.selectbox(f'Select Location Type', location_type_options, index=location_type_options.index(default_location_type), key=f"{file.name}_type")

    return local_dates, location_names, ssid, location_type

def calculate_distinct_count(df, local_dates, location_names, ssid, location_type):
    results_df = pd.DataFrame(columns=['Local Date', 'Location Name', 'Distinct Count'])
    for local_date in local_dates:
        for location_name in location_names:
            filtered_df = df[(df['Local Date'] == local_date) & 
                             (df['Location Name'] == location_name) & 
                             (df['Location Type'] == location_type) & 
                             (df['SSID'].isin(ssid))]

            distinct_count = filtered_df['User Name'].nunique()

            result = pd.DataFrame({'Local Date': [local_date], 'Location Name': [location_name], 'Distinct Count': [distinct_count]})
            results_df = pd.concat([results_df, result])

    results_df['Local Date'] = results_df['Local Date'].astype(str)

    return results_df

def visualize_results(results_df, file):
    file_name = file if isinstance(file, str) else file.name
    st.subheader(f"Results for {file_name}:")
    show_table = st.checkbox("Show Table", value=True, key=f"{file_name}_show_table")
    if show_table:
        st.write(results_df)

    show_chart = st.checkbox("Show Chart", value=True, key=f"{file_name}_show_chart")
    if show_chart:
        st.altair_chart(alt.Chart(results_df).mark_line().encode(
            x='Local Date:T',
            y='Distinct Count:Q',
            color='Location Name:N',
            tooltip=['Local Date', 'Location Name', 'Distinct Count']
        ).interactive(), use_container_width=True)

def download_link(df, filetype, filename):
    if filetype == "csv":
        data = df.to_csv(index=False)
        b64 = base64.b64encode(data.encode()).decode()  # some strings <-> bytes conversions necessary here
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download {filename} as CSV</a>'
    elif filetype == "xlsx":
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)
        xlsx_data = output.getvalue()
        b64 = base64.b64encode(xlsx_data).decode()  # some strings <-> bytes conversions necessary here
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Download {filename} as XLSX</a>'
    return href

def analyze_file(file):
    df = load_data(file)

    if df is not None:
        local_dates, location_names, ssid, location_type = get_user_inputs(df, file)
        if local_dates and location_names and ssid:
            results_df = calculate_distinct_count(df, local_dates, location_names, ssid, location_type)
            visualize_results(results_df, file)
            return results_df

    return pd.DataFrame()

st.sidebar.image("location-analytics.png")  # Add an image to make the interface more appealing
st.title('User Analysis App')
st.write("""
This app allows you to perform an analysis on user data. After uploading your data files, 
you can select specific dates, locations, and SSIDs to see the distinct 
count of User Names for each combination of the selected values. The results from two files can be merged.
""")

file1 = st.sidebar.file_uploader('Upload your first Excel or CSV file', type=['csv', 'xls', 'xlsx', 'xlsm'], key="file1")
file2 = st.sidebar.file_uploader('Upload your second Excel or CSV file', type=['csv', 'xls', 'xlsx', 'xlsm'], key="file2")

reset_button = st.sidebar.button("Reset")
if reset_button:
    file1, file2 = None, None

if file1 is not None and file2 is not None:
    st.write("## Analysis for File 1")
    results1 = analyze_file(file1)

    st.write("## Analysis for File 2")
    results2 = analyze_file(file2)

    if not results1.empty and not results2.empty:
        st.write("## Merged Results")
        merged_df = pd.concat([results1, results2]).drop_duplicates()
        visualize_results(merged_df, 'Merged Files')

        st.markdown(download_link(merged_df, 'csv', 'merged_results.csv'), unsafe_allow_html=True)
        st.markdown(download_link(merged_df, 'xlsx', 'merged_results.xlsx'), unsafe_allow_html=True)

else:
    st.write('Please upload two files.')
