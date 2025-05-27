# -----------------------------------------------------------------------------
# This project was independently created and developed.
# Some parts of the code were enhanced with the help of ChatGPT to improve efficiency and debug errors.
# All final design, logic, and decisions are the creator’s own effort and vision.
# -----------------------------------------------------------------------------

# Import libraries 
import streamlit as st
import pandas as pd
import altair as alt

# set project version
projectversion = 1.0


# Define the column order for the finance tracker. "Select" is the first column to facilitate row selection.
COLS_ORDER = ["Select", "Date", "Name", "Description", "Amount", "Category", "Type", "Currency", "Payment Method", "Project"]

# Create a function to sanitize the user input. This function removes commas from user-input strings to prevent issues with CSV formatting.
def sanitize_input(s):
    if s is None:
        return s
    return s.replace(",", "")

# We use st.session_state to store data so that it persists across interactions. st.session_state is a special Streamlit feature that remembers values across reruns.
if "data" not in st.session_state: # Check if "data" does not already exist in st.session_state
    st.session_state.data = pd.DataFrame(columns=COLS_ORDER) # If not, create it and set it to an empty DataFrame
	
if "uploaded_file" not in st.session_state: #do the same for "uploaded file"
    st.session_state.uploaded_file = None
	
if "data_loaded" not in st.session_state: #do the same for "data_loaded"
    st.session_state.data_loaded = False
		
# -----------------------------------------------------------------------------
# CREATE A SIDEBAR
# -----------------------------------------------------------------------------

#create the title of the project
st.sidebar.header("BudgetBuddy")
st.sidebar.divider()

# create a expander to filter the time span
with st.sidebar.expander(":clock9: Select Time Span", expanded=False):
    st.write(":information_source: *Please select a time span you would like to analyse. You can either select a week, month, year or a custom time span.*") #write some information
    today = pd.Timestamp.today().normalize() # store today's date with the time normalized to midnight
    time_option = st.selectbox("Select Time Span", options=["Week", "Month", "Year", "Custom"], index=2) #dropdown to select a time span type

    if time_option == "Week": # check if the user selected "Week". For weeks, user needs to select a year and a week number
        selected_year = st.selectbox("Which Year?", options=range(2000, today.year + 2), index=today.year - 2000)
        selected_week = st.selectbox("Which Week?", options=range(1, 54), index=today.isocalendar().week - 1)
        # Calculate start (Monday) and end (Sunday) dates for that week.
        start_date = pd.Timestamp.fromisocalendar(selected_year, selected_week, 1) # create a Timestamp from a year, ISO week number and day of the week
        end_date = pd.Timestamp.fromisocalendar(selected_year, selected_week, 7)
		
    elif time_option == "Month": # check if the user selected "Month". For months, user needs to select a year and a month number
        selected_year = st.selectbox("Which Year?", options=range(2000, today.year + 2), index=today.year - 2000)
        selected_month = st.selectbox("Which Month?", options=list(range(1, 13)), index=today.month - 1)
        start_date = pd.Timestamp(year=selected_year, month=selected_month, day=1) # create a Timestamp from a year, month and day of the week
        end_date = start_date + pd.offsets.MonthEnd(1) # add one month to the start date
		
    elif time_option == "Year": # check if the user selected "Year". For years, user needs to select a year
        selected_year = st.selectbox("Which Year?", options=range(2000, today.year + 2), index=today.year - 2000)
        start_date = pd.Timestamp(year=selected_year, month=1, day=1) # create a Timestamp from a year, month and day of the week
        end_date = pd.Timestamp(year=selected_year, month=12, day=31)
		
    elif time_option == "Custom": # check if the user selected "Custom". For customs, user needs to select two dates in the datepicker
        custom_range = st.date_input("Which date span?", value=(today - pd.Timedelta(days=7), today))
        if isinstance(custom_range, (list, tuple)) and len(custom_range) == 2: # check if the user selected two dates (checks if the custom_range is a list or tuple)
            start_date, end_date = pd.to_datetime(custom_range[0]), pd.to_datetime(custom_range[1]) # convert both selected dates into pandas Timestamp objects
        else: #display info-message
            st.error(":grey_exclamation: Please select a valid timerange and add an enddate.")
            start_date = today - pd.Timedelta(days=7)
            end_date = today

# create a expander to show different options for data handling (Reset, Upload, Load, and Export)
with st.sidebar.expander(":card_index_dividers: Data Options", expanded=False):
    st.write(":information_source: *You can either reset all the data and start with your own or you can import a file.*") #write some information
	
    # Reset Data when a button is clicked
    if st.button(":wastebasket: Start from scratch and reset data"): #create button
        st.session_state.data = pd.DataFrame(columns=COLS_ORDER) # Reset the data to an empty DataFrame with the correct column order
        st.session_state.uploaded_file = None # Clear any previously uploaded file
        st.session_state.data_loaded = False # Mark that no data is currently loaded
        st.success("Data reset to an empty dataset.") # Show a success message

    # Upload CSV file when a button is clicked
    uploaded_file = st.file_uploader("Upload your own CSV", type=["csv"])
    if uploaded_file is not None: # check if a file was uploaded
        st.session_state.uploaded_file = uploaded_file #load it into the session.state

    # Load CSV file when a button is clicked
    if st.button(":outbox_tray: Load CSV into the tracker"):
        if st.session_state.uploaded_file is not None: # heck if a file was uploaded
            try:
                df = pd.read_csv(st.session_state.uploaded_file) # set dataframe
                # check if the uploaded file has all the required columns (excluding "Select")
                required = set(COLS_ORDER) - {"Select"}
                missing_cols = [col for col in required if col not in df.columns] # if required column is not in the dataframe, add it to the missing columns
                if missing_cols:
                    st.error("CSV is missing required columns: " + ", ".join(missing_cols)) # inform the user about a invalid csv file
                else: # else everything is good
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce") # convert the "Date" column to datetime
                    df["Amount"] = df["Amount"].astype(str).str.replace(",", "", regex=False).str.replace("'", "", regex=False) # clean up the "Amount" column: convert into string, remove commas/apostrophes
                    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce") # after clean up, convert into numeric
                    mask_expense = df["Type"].str.lower().isin(["expense", "expenses"]) # Create a mask for rows where "Type" is "expense" or "expenses" (case-insensitive).
                    df.loc[mask_expense, "Amount"] = -df.loc[mask_expense, "Amount"].abs() # Set all expense amounts to negative (force positive first, then negate)
                    df.loc[~mask_expense & (df["Type"].str.lower() == "income"), "Amount"] = df.loc[~mask_expense & (df["Type"].str.lower() == "income"), "Amount"].abs() # Set all income amounts to positive (force positive).
                    if "Select" not in df.columns: # If "Select" column doesn't exist, add it with default value False for all rows
                        df["Select"] = False
                    df = df[COLS_ORDER] # reorder the dataframe columns to match the predefined order (COLS_ORDER)
                    st.session_state.data = df # Save the cleaned and processed dataframe into session state
                    st.session_state.data_loaded = True # Mark that data has been successfully loaded
                    st.success(":white_check_mark: CSV was loaded successfully!") # inform user about success
            except Exception as e:
                st.error("Error loading CSV: " + str(e)) # inform user about error
        else:
            st.info(":grey_exclamation: Please upload a CSV file first.") # If no file was uploaded, inform the user

    # Export data when a button is clicked
    csv = st.session_state.data.to_csv(index=False).encode("utf-8") # Convert the session data to CSV format and encode it
    st.download_button(label=":inbox_tray: Export Data", data=csv, file_name="data_export.csv", mime="text/csv") # Create a download button

# create a expander to show information about this project
with st.sidebar.expander(":information_source: About This Project", expanded=False):
    st.write("""

    This coding project is your next Finance Tracker! You can enter and manage your income as well as your expenses. Allowing a deeper understanding using detailed analyses. You can also import and export files.

    ---
    
    **Developed by:**  
    *ah_codes*  
    *Mike22*  
    **Developed for:**   
    Skills: Programming with Advanced Computer Languages
	
    ---
    """)
    st.write("Please use Streamlit Version 1.45.1 or newer. Your current version is:", st.__version__) #remind user to check fot the current streamlit version installed
    st.write("Project Version:", projectversion) # display the current version of the app
		
# -----------------------------------------------------------------------------
# MAIN AREA
# -----------------------------------------------------------------------------

# Filter data based on time span
data_all = st.session_state.data.copy() # Make a copy of the main DataFrame to avoid modifying original data
data_all["Date"] = pd.to_datetime(data_all["Date"], errors="coerce") # Ensure the "Date" column is properly converted to datetime format
filtered_data = data_all[(data_all["Date"] >= start_date) & (data_all["Date"] <= end_date)] # Filter data to include only rows within the selected date range

# Display total income and expense metrics
col1, col2 = st.columns(2) # Create two side-by-side columns
with col1:
    total_income = filtered_data.loc[filtered_data["Type"] == "Income", "Amount"].sum() # Calculate the total income amount
    st.metric(":chart_with_upwards_trend: Total Income", f"{total_income:.2f}") # Display total income as a metric
with col2:
    total_expense = filtered_data.loc[filtered_data["Type"] == "Expense", "Amount"].sum() # Calculate the total expense amount
    st.metric(":chart_with_downwards_trend: Total Expense", f"{total_expense:.2f}") # Display total expense as a metric

# Create a section/expander to add a new entry
with st.expander(":pencil2: Add New Entry", expanded=False): # Create an expandable section
    st.subheader("Please enter the details of the new entry")
    with st.form("entry_form", clear_on_submit=True): # Create a form that clears itself after submission
        col1, col2, col3 = st.columns(3) # Divide the form into three columns for better layout
        with col1:
            date_entry = st.date_input("Date") # Input for selecting the date
            name_entry = sanitize_input(st.text_input("Name")) # Text input for the name (sanitized)
            description_entry = sanitize_input(st.text_input("Description")) # Text input for description (sanitized)
        with col2:
            amount_entry = st.number_input("Amount", value=0.0, min_value=0.0, step=0.05, format="%.2f") # Number input for amount (only positive)
            category_entry = sanitize_input(st.text_input("Category")) # Text input for category (sanitized)
            type_entry = st.selectbox("Type", options=["Income", "Expense"]) # Selectbox to choose between Income and Expense
        with col3:
            currency_entry = sanitize_input(st.text_input("Currency")) # Text input for currency (sanitized)
            payment_method_entry = st.selectbox("Payment Method", options=["Debit Card", "Credit Card", "Cash", "Bank Transfer", "Paypal"]) # Select payment method
            project_entry = sanitize_input(st.text_input("Project")) # Text input for project name (sanitized)
        submitted = st.form_submit_button(":heavy_plus_sign: Add new entry") # Create a submit button for the form
        if submitted:
            amount_val = -abs(amount_entry) if type_entry == "Expense" else abs(amount_entry) # Make amount negative for expenses, positive for income
            new_entry = { # Create a dictionary for the new entry with all fields
                "Select": False,
                "Date": pd.to_datetime(date_entry),
                "Name": name_entry,
                "Description": description_entry,
                "Amount": amount_val,
                "Category": category_entry,
                "Type": type_entry,
                "Currency": currency_entry,
                "Payment Method": payment_method_entry,
                "Project": project_entry
            }
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_entry])], ignore_index=True) # Add the new entry to the session data
            st.success(":white_check_mark: New entry was added successfully!") # Show a success message
            st.rerun() # Rerun the app to refresh everything

# Display and edit entries
st.write(":information_source: *The following table shows you all the entries you tracked during the selected time span. Select a row to edit your entries.*") # Add an information message
if filtered_data.empty:
    st.info(":grey_exclamation: There is currently no data available for the selected time span.") # Show an info box if there are no entries
else:
    display_data = filtered_data[COLS_ORDER] # Reorder columns for displaying
    edited_df = st.data_editor(display_data, key="data_editor", num_rows="dynamic", use_container_width=True) # Display an interactive editable table
    for idx in edited_df.index:
        st.session_state.data.loc[idx] = edited_df.loc[idx] # Update the session data with changes made in the editor
    selected_indices = edited_df.index[edited_df["Select"] == True].tolist() # Get a list of selected row indices based on the "Select" checkbox
    if len(selected_indices) == 1: # If exactly one row is selected, show an edit form for that entry
        idx = selected_indices[0] # Get the index of the single selected row
        st.write(":information_source: *You can now change the details of the selected entry.*") # Add an information message
        entry = st.session_state.data.loc[idx].copy() # Copy the selected entry's data
        with st.form("edit_form"): # Create a form for editing the entry
            col1, col2, col3 = st.columns(3) # Create layout for the form
            with col1:
                edited_date = st.date_input("Date", value=entry["Date"]) # Date input field
                edited_name = sanitize_input(st.text_input("Name", value=entry["Name"])) # Text input for name (sanitized)
                edited_description = sanitize_input(st.text_input("Description", value=entry["Description"])) # Text input for description (sanitized)
            with col2:
                edited_amount = st.number_input("Amount", value=float(abs(entry["Amount"])), min_value=0.0, step=0.1, format="%.2f") # Number input for amount (always positive)
                edited_category = sanitize_input(st.text_input("Category", value=entry["Category"])) # Text input for category (sanitized)
                edited_type = st.selectbox("Type", options=["Income", "Expense"], index=0 if entry["Type"] == "Income" else 1) # Selectbox for type (Income/Expense)
            with col3:
                edited_currency = sanitize_input(st.text_input("Currency", value=entry["Currency"])) # Text input for currency (sanitized)
                options_pm = ["Debit Card", "Credit Card", "Cash", "Bank Transfer", "Paypal"] # List of payment method options
                default_idx = options_pm.index(entry["Payment Method"]) if entry["Payment Method"] in options_pm else 0 # Find the default payment method index
                edited_payment_method = st.selectbox("Payment Method", options=options_pm, index=default_idx) # Selectbox for payment method
                edited_project = sanitize_input(st.text_input("Project", value=entry["Project"])) # Text input for project (sanitized)
            save_btn = st.form_submit_button(":floppy_disk: Save changes") # Button to save changes
            delete_btn = st.form_submit_button(":wastebasket: Delete entry") # Button to delete the entry
            if save_btn:
                st.session_state.data.at[idx, "Date"] = pd.to_datetime(edited_date) # Save edited date
                st.session_state.data.at[idx, "Name"] = edited_name # Save edited name
                st.session_state.data.at[idx, "Description"] = edited_description # Save edited description
                if edited_type == "Expense":
                    st.session_state.data.at[idx, "Amount"] = -abs(edited_amount) # Save amount as negative for expenses
                else:
                    st.session_state.data.at[idx, "Amount"] = abs(edited_amount) # Save amount as positive for income
                st.session_state.data.at[idx, "Category"] = edited_category # Save edited category
                st.session_state.data.at[idx, "Type"] = edited_type # Save edited type
                st.session_state.data.at[idx, "Currency"] = edited_currency # Save edited currency
                st.session_state.data.at[idx, "Payment Method"] = edited_payment_method # Save edited payment method
                st.session_state.data.at[idx, "Project"] = edited_project # Save edited project name
                st.session_state.data.at[idx, "Select"] = False # Unselect the row after editing
                st.success("Entry updated successfully!") # Show a success message
                st.rerun() # Rerun the app to refresh everything
            elif delete_btn:
                st.session_state.data = st.session_state.data.drop(idx).reset_index(drop=True) # Delete the selected row and reset the index
                st.success("Entry deleted successfully!") # Show a success message after deletion
                st.rerun() # Rerun the app to refresh everything
    elif len(selected_indices) > 1:
        st.warning("Please select only one entry for editing.") # Warn if multiple rows are selected for editing

# Analysing data
st.header("Analysis of your Income and Expenses") # Header for the analysis section

# Bar-charts
st.write(":information_source: *The following bar-charts show you all the entries you tracked during the selected time span. They are grouped by the selected option and display your incomes and expenses over time.*") # Info text explaining the bar charts
if filtered_data.empty:
    st.info(":grey_exclamation: No data available for analysis in the selected time span.") # Show info if there's no data to analyse
else:
    group_by_option_bar_chart = st.selectbox("Group analysis by", options=["Project", "Payment Method", "Category", "Type", "Currency"], index=0) # Dropdown to choose how to group the bar charts
    for grp in filtered_data[group_by_option_bar_chart].unique(): # Loop through each group in the selected category
        grp_data = filtered_data[filtered_data[group_by_option_bar_chart] == grp].copy()  # Filter data for the current group
        grp_data.sort_values("Date", inplace=True) # Sort group data by date
        grouped = grp_data.groupby("Date", as_index=False)["Amount"].sum() # Group by date and sum the amounts
        total_value = grp_data["Amount"].sum() # Calculate total value for the group
        chart = alt.Chart(grouped).mark_bar().encode( # Create a bar chart using Altair
            x=alt.X("Date:T", title="Date", axis=alt.Axis(format="%d. %m. %Y")), # Set x-axis as Date and force altair to use a specific date-format
            y=alt.Y("Amount:Q", title="Amount"), # Set y-axis as Amount
            color=alt.condition(alt.datum.Amount >= 0, alt.value("green"), alt.value("red")) # Color bars green for positive and red for negative amounts
        ).properties(width=200, height=200) # Set the size of the chart
        col1, col2, col3 = st.columns([1, 2, 1]) # Create layout with three columns (narrow-wide-narrow)
        with col1:
            st.write(f"**{grp}**") # Show the group name
        with col2:
            st.altair_chart(chart, use_container_width=True) # Display the chart in the middle column
        with col3:
            st.write(f"**Total: {total_value:.2f}**") # Show total amount for the group

# Pie chart
st.write(":information_source: *The following pie-chart shows you all the entries you tracked during the selected time span. They are grouped by the selected option.*") # Info text explaining the pie chart
if filtered_data.empty:
    st.info(":grey_exclamation: No data available for the pie chart in the selected time span.") # Show info if no data for pie chart
else:
    group_by_option_pie_chart = st.selectbox("Group analysis by", options=["Project", "Payment Method", "Category", "Type", "Currency"], index=2) # Dropdown to select pie chart grouping
    pie_data = filtered_data.groupby(group_by_option_pie_chart, as_index=False)["Amount"].sum() # Group data by selected option and sum amounts
    pie_chart = alt.Chart(pie_data).mark_arc(innerRadius=50).encode( # Create a donut pie chart with an inner radius
        theta=alt.Theta(field="Amount", type="quantitative", aggregate="sum"), # Set slice size based on Amount
        color=alt.Color(field=group_by_option_pie_chart, type="nominal"), # Color slices based on grouping
        tooltip=[group_by_option_pie_chart, alt.Tooltip("Amount", format=".2f")]  # Add tooltips showing group name and amount
    ).properties(width=400, height=400) # Set the size of the pie chart
    st.altair_chart(pie_chart, use_container_width=True) # Display the pie chart
