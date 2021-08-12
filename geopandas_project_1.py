# -*- coding: utf-8 -*-
"""
Created on Tue Aug  3 21:18:52 2021

@author: JackSullivan
"""

def choropleth(data_filepath, excel_sheet_name, fname, client_data_postcode_column_header, postcode_lad_filepath, shapefile_filepath, weighted_column, weighted_column_type):
    """Produce a choropleth map based on the inputted data"""
    # Import the necessary libraries
    import pandas as pd
    from matplotlib import pyplot as plt
    import geopandas as gpd
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    # Read in OAC's client data
    try:
        if data_filepath.endswith(".csv"):
            client_data = pd.read_csv(data_filepath)
        elif data_filepath.endswith(".xlsx"):
            client_data = pd.read_excel(data_filepath, excel_sheet_name)
        elif data_filepath.endswith(".json"):
            client_data = pd.read_json(data_filepath)
        elif data_filepath.endswith(".tsv"):
            client_data = pd.read_csv(f"{data_filepath}, sep='\t'")
    except NameError:
        print(
            "You need to move the data format into a csv, tsv, xlsx (excel), or json format")
        exit()

    # Now we need to clean up the client data, to have it in the exact
    # same format (amount of spaces) as the postcode_lsoa data that we'll see later
    series = list(client_data[client_data_postcode_column_header])
    series_1 = []

    for postcode in series:
        try:
            if len(postcode) == 7:
                series_1.append(postcode)
            elif len(postcode) == 8:
                a = str(postcode).replace(" ", "")
                series_1.append(a)
            elif len(postcode) == 6:
                a = str(postcode).replace(" ", "  ")
                series_1.append(a)
            elif len(postcode) == 5:
                a = f"{postcode[0:2]}  {postcode[2:]}"
                series_1.append(a)
            else:
                # Still return the faulty data to the client dataset because it will be lost on a later merge.
                series_1.append(postcode)
        except TypeError:
            series_1.append(postcode)

    # Add our modified postcodes back to the dataframe, remove the old postcode column, and rename the newer column

    client_data['Postcodes_cleaned'] = series_1
    client_data.drop(columns=[client_data_postcode_column_header], inplace=True)
    client_data = client_data.rename(
        index=str, columns={"Postcodes_cleaned": "Postcode"})

    # Read in the ONS data which gives the corresponding LSOA value to
    # each UK postcodes
    postcode_lad = pd.read_csv(postcode_lad_filepath, low_memory=False)

    # Reduce the dataframe to the necessary columns
    postcode_lad = postcode_lad[['pcd7', 'lsoa11cd', 'ladnm']]
    # Rename the column headers
    postcode_lad = postcode_lad.rename(
        index=str, columns={"pcd7": "Postcode", "lsoa11cd": "LSOA", "ladnm": "LAD"})

    # Merge the two dataframes on the common postcode column
    first_merge = pd.merge(client_data, postcode_lad, on="Postcode")

    # If weighting variable is equal to 'PolicyCount' then create a policy count dataframe.
    if weighted_column_type == 'PC':
        policy_count = first_merge['LAD'].value_counts()
        count_dict = {'LAD': [], 'PolicyCount': []}

        for lad, count in policy_count.items():
            count_dict['LAD'].append(lad)
            count_dict['PolicyCount'].append(count)

        policy_count_dataframe = pd.DataFrame(count_dict)

    # Use Geopandas to read in the ONS shapefile into a geodataframe

    map_df = gpd.read_file(shapefile_filepath)

    # Rename the column headers
    map_df = map_df.rename(index=str, columns={"LAD21NM": "LAD"})

    # Join the map geodataframe to the dataframe. Set each index to LAD,
    # this should mean that each local authority district stays in our
    # geodataframe, and we avoid duplicate districts.

    if weighted_column_type == 'MV':
        merged_gdf_df = map_df.set_index(
            "LAD").join(first_merge.set_index("LAD"))
        #merged_gdf_df = pd.merge(map_df, first_merge, on="LAD")
    elif weighted_column_type == 'PC':
        #policy_count_merge = pd.merge(map_df, policy_count_dataframe, on="LAD")
        policy_count_merge = map_df.set_index("LAD").join(
            policy_count_dataframe.set_index("LAD"))

    merged_gdf_df.to_csv("final_dataframe.csv", mode='a')
    
    #### Commented out this section, will look to include it later ####
    # # Amplify the values in the SumAssured column
    # def update_SumAssured(value):
    #     """Multiply values in the SumAssured series by 1000"""
    #     return value*10000

    # merged_gdf_df['SumAssured'] = merged_gdf_df['SumAssured'].apply(update_SumAssured)
    # merged_gdf_df['SumAssured'] = merged_gdf_df['SumAssured']/ 1_000_000

    # Mapping the choropleth.

    # set the range for the choropleth
    # vmin, vmax = 120, 220

    # Create a figure for the  plot
    fig, ax = plt.subplots(1, figsize=(10, 6))
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.1)

    # Plot the map that goes inside the figure
    if weighted_column_type == 'MV':
        merged_gdf_df.plot(column=weighted_column, cmap='Blues', linewidth=0.8, ax=ax,
                           edgecolor='0.8', legend=True, legend_kwds={'label': "Policy Value per Local Authority District"}, cax=cax)
    elif weighted_column_type == 'PC':
        policy_count_merge.plot(column=weighted_column, cmap='Blues', linewidth=0.8, ax=ax,
                                edgecolor='0.8', legend=True, legend_kwds={'label': "Policy Value per Local Authority District"}, cax=cax)

    # Set the title
    ax.set_title(f"UK Postcode Exposure (weighted by {weighted_column})", fontsize=10)
    # Remove the axes
    ax.set_axis_off()

    plt.show()
    # Save the figure to the specified filename
    plt.savefig(fname, bbox_inches='tight')


data_filepath = "postcode_sample_filev2.csv"
excel_sheet_name = '2019 risk'
data_filepath_1 = "Caravan Data.xlsx"
fname = "choropleth_map_sample_data_SumAssured.png"
client_data_postcode_column_header = "Postcode"
postcode_lad_filepath = "postcode_to_lad"
shapefile_filepath = "Local_Authority_Districts_(May_2021)_UK_BUC\Local_Authority_Districts_(May_2021)_UK_BUC.shp"
weighted_column='SumAssured'
# If the weighted column is a market value, enter 'MV' for the following variable. 
# or if the weighted column is based on policy count type 'PC' 
weighted_column_type = 'MV'

choropleth(data_filepath, excel_sheet_name, fname, client_data_postcode_column_header, postcode_lad_filepath, shapefile_filepath, weighted_column, weighted_column_type)


