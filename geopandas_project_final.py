# -*- coding: utf-8 -*-
"""
Created on Fri Aug 27 16:43:41 2021

@author: JackSullivan
"""

def choropleth(data_filepath, excel_sheet_name, fname, client_data_postcode_column_header, postcode_lad_filepath, shapefile_filepath, market_value_column_name, policy_count_column_name, weighted_column, weighted_column_type):
    """Produce a choropleth map based on the inputted data"""
    # Import the necessary libraries
    import pandas as pd
    from matplotlib import pyplot as plt
    import geopandas as gpd
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    
    ### Use Geopandas library to read in the ONS shapefile into a geodataframe ###
    map_df = gpd.read_file(shapefile_filepath)

    # Rename the column headers
    map_df = map_df.rename(index=str, columns={"LAD21NM": "LAD"})


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
    # same format (amount of spaces) as the postcode_lsoa data that we'll see 
    # later
    
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
                # Still return the faulty data to the client dataset because it
                # will be lost on a later merge.
                series_1.append(postcode)
        except TypeError:
            series_1.append(postcode)

    # Add our modified postcodes back to the dataframe, remove the old postcode
    # column, and rename the newer column as Postcode

    client_data['Postcodes_cleaned'] = series_1
    client_data.drop(columns=[client_data_postcode_column_header], inplace=True)
    client_data = client_data.rename(
        index=str, columns={"Postcodes_cleaned": "Postcode"})

    
    # Read in the ONS data which gives the corresponding LAD name to
    # each UK postcode
    postcode_lad = pd.read_csv(postcode_lad_filepath, low_memory=False)

    # Reduce the dataframe to the necessary columns
    postcode_lad = postcode_lad[['pcd7', 'lsoa11cd', 'ladnm']]
    # Rename the column headers
    postcode_lad = postcode_lad.rename(
        index=str, columns={"pcd7": "Postcode", "lsoa11cd": "LSOA",
                            "ladnm": "LAD"})

    # Merge the two dataframes on the common postcode column
    first_merge = pd.merge(client_data, postcode_lad, on="Postcode")
    
    # Create a new dataframe with one aggregated MV value per postcode 
    # This dataframe will be useful later in extracting the number of unique postcodes 
    # for which we have data for
    a = first_merge.groupby(['Postcode', 'LAD'],
                            as_index=False)[market_value_column_name].sum()
    
    # Now create a new dataframe from this new dataframe which has the aggregate 
    # Market Value (MV) of the policies held in each LAD. Call this mv_dataframe. 
    mv_dataframe = a.groupby(['LAD'], as_index=False)[market_value_column_name].sum()

    # Create another new dataframe with the policy count per LAD (the number of
    # policies held by households in each LAD). Call this pc_dataframe
    policy_count = first_merge['LAD'].value_counts()
    count_dict = {'LAD': [], policy_count_column_name: []}

    for lad, count in policy_count.items():
        count_dict['LAD'].append(lad)
        count_dict[policy_count_column_name].append(count)

    pc_dataframe = pd.DataFrame(count_dict)
    
    # Merge these two newly created dataframes, mv_dataframe and pc_dataframe. This 
    # gives a dataframe with one row per LAD, with a PolicyCount and MV column. 
    # Name it mv_pc_df
    mv_pc_df = pd.merge(pc_dataframe, mv_dataframe, on='LAD')
    
    
    # Now we need to add the LAD's which are missing from mv_pc_df and give 
    # each of these districts an aggregate market value and policy count of 0.
    # In doing this we'll create a new dataframe called complete_df
    all_lad_list = list(map_df['LAD'])
    
    # LAD's accounted for in our data 
    mapped_lads = mv_pc_df['LAD']
    mapped_lads_list = list(mapped_lads)
    
    # Obtain a list for the missing LAD's (the LAD's not in our final_clean_df)
    missing_lads = [lad for lad in all_lad_list if lad not in mapped_lads_list]
    
    a = {'LAD': [], policy_count_column_name: [], market_value_column_name: []}
    for missing_lad in missing_lads:
        a['LAD'].append(missing_lad)
        a[policy_count_column_name].append(0)
        a[market_value_column_name].append(0)
            
        
    missing_lads_df = pd.DataFrame(a)
    complete_df = mv_pc_df.append(missing_lads_df, ignore_index=True)
    
       
    # Merge our map geodataframe to our dataframe with the MV and PolicyCount
    # columns. 
    merged_gdf_df = pd.merge(map_df, complete_df, on="LAD")
    
    # Write our final geodataframe to a csv file 
    merged_gdf_df.to_csv("final_geodataframe.csv", mode='w')

    
    ######         Mapping the choropleth          ######

    # Create a figure for the plot
    fig, ax = plt.subplots(1, figsize=(10, 6))
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.1)

    # Plot the choropleth map inside the figure
    if weighted_column_type == 'MV':
        legend_title = "Policy Value per Local Authority District (£)"
    if weighted_column_type == 'PC':
        legend_title = "Number of Policies per Local Authority District"
    
    merged_gdf_df.plot(column=weighted_column, cmap='Blues', linewidth=0.3, ax=ax,
                           edgecolor='0.8', legend=True, legend_kwds={'label': legend_title}, cax=cax)
                     
    # Set the title
    ax.set_title(f"UK Postcode Exposure (weighted by {weighted_column})", fontsize=11)
   
    # Set the subtitle 
    plt.suptitle(f"Data plotted for {len(series)} postcodes in {len(merged_gdf_df['LAD'])} Local Authority Districts", fontsize=7)

    # Remove the axes
    ax.set_axis_off()

    plt.show()
    # Save the figure to the specified filename
    plt.savefig(fname, bbox_inches='tight')


data_filepath = "postcode_sample_filev2.csv"
excel_sheet_name = '2019 risk'
data_filepath_1 = "Caravan Data.xlsx"
fname = "choropleth_map_sample_data_MV.png"
client_data_postcode_column_header = "Postcode"
postcode_lad_filepath = "postcode_to_lad"
shapefile_filepath = "Local_Authority_Districts_(May_2021)_UK_BUC\Local_Authority_Districts_(May_2021)_UK_BUC.shp"
market_value_column_name='SumAssured'
policy_count_column_name='PolicyCount'
weighted_column='SumAssured'


# If the weighted column is a market value, enter 'MV' for the following variable. 
# or if the weighted column is based on policy count type 'PC' 
weighted_column_type = 'MV'


choropleth(data_filepath, excel_sheet_name, fname, client_data_postcode_column_header, postcode_lad_filepath, shapefile_filepath, market_value_column_name, policy_count_column_name, weighted_column, weighted_column_type)
