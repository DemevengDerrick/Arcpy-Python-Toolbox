# -*- coding: utf-8 -*-

import arcpy
import pandas as pd
import os

# for ONA Connector-
import odk_funtions
import importlib
importlib.reload(odk_funtions)  # force reload of the module
from arcgis.features import GeoAccessor, GeoSeriesAccessor
from odk_funtions import Ona


workspace_path = arcpy.env.workspace
arcpy.env.overwriteOutput = True

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "AFRO_GIS_Center"
        self.alias = "WHO AFRO GIS Center Toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [RandomPointGenerator, OnaConnector, VirusMapping, VirusMappingCPD]

#============================================Random Point Mapping===================================================
class RandomPointGenerator(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Random Point Generator"
        self.description = "Random point generator is a tool to generate random points within a certain polygon boundary based on an input linelist in .xls, .xlsx, and .csv"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        excel_file = arcpy.Parameter(name="excel_file",
                                     displayName="Excel File",
                                     direction="Input",
                                     datatype="DEFile",
                                     parameterType="Required")
        
        excel_file.filter.list = ['xls', 'xlsx', 'csv']
        
        field_name = arcpy.Parameter(name="field_name",
                                     displayName="Field Name",
                                     direction="Input",
                                     datatype="GPString",
                                     parameterType="Required",
                                     multiValue="True")
        
        admin_layer = arcpy.Parameter(name="admin_layer",
                                     displayName="Admin Layer",
                                     direction="Input",
                                     datatype="GPFeatureLayer",
                                     parameterType="Required")
        
        admin_field_name = arcpy.Parameter(name="admin_field_name",
                                     displayName="Admin Field Name",
                                     direction="Input",
                                     datatype="GPString",
                                     parameterType="Required",
                                     multiValue="True")

        """ sql_clause = arcpy.Parameter(name="SQL",
                                     displayName="SQL",
                                     direction="Input",
                                     datatype="GPSQLExpression",
                                     parameterType="Required") """
        try:
            # get the current map
            mxd = arcpy.mp.ArcGISProject("CURRENT")
            map = mxd.activeMap

            # get a list of layer objects in the map
            layers = map.listLayers()

            # add the layer names to the parameter's value list
            value_list = [layer.name for layer in layers]
            admin_layer.filter.list = value_list
        except:
            pass
        
        params = [excel_file, field_name, admin_layer, admin_field_name]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, params):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if params[0].valueAsText:
            if params[0].valueAsText.split("\\")[-1].endswith(".csv"):
                excel_to_pd = pd.read_csv(params[0].valueAsText)
            else:
                excel_to_pd = pd.read_excel(params[0].valueAsText)
            
        columns = excel_to_pd.columns
        params[1].filter.list = sorted(columns.tolist())

        if params[2].valueAsText:
            field_objects = arcpy.ListFields(params[2].valueAsText)
            field_names = [field.name for field in field_objects]
            params[3].filter.list = sorted(field_names)

        return excel_to_pd

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, params, messages):
        """The source code of the tool."""
        #select by attribute of admin feature to generate point within
        if params[0].valueAsText.split("\\")[-1].endswith(".csv"):
            excel_to_pd = pd.read_csv(params[0].valueAsText)
        else:
            excel_to_pd = pd.read_excel(params[0].valueAsText)

        excel_to_pd["Lon(X)"] = ""
        excel_to_pd["Lat(Y)"] = ""

        input_fields = params[1].valueAsText.split(";")
        admin_fields = params[3].valueAsText.split(";")
        
        excel_to_pd.sort_values(by=input_fields[2])
        #admin_values = sorted(excel_to_pd[admin_field].tolist())
        selected_layer = ""
        test_value = "" #value used to test if the previously selected admin is not equal to the new
        for i, row in excel_to_pd.iterrows():
            country = row[input_fields[0]]
            province = row[input_fields[1]]
            district = row[input_fields[2]]
            
            if test_value == district:
                selected_count = int(arcpy.management.GetCount(selected_layer).getOutput(0))

                if selected_count > 0:
                    arcpy.CreateRandomPoints_management(workspace_path, "randPoint", selected_layer, "", 1)
                    
                    with arcpy.da.SearchCursor("randPoint", ["SHAPE@XY"]) as cursor:
                        for row in cursor:
                            # extract the x and y coordinates
                            x, y = row[0]
                else:
                    x, y = ["",""]
            else:
                #arcpy.AddMessage(admin_field)
                #arcpy.AddMessage(admin_value)
                query = f"{admin_fields[0]} = '{country}' And {admin_fields[1]} = '{province}' And {admin_fields[2]} = '{district}'"
                #arcpy.AddMessage(query)
                selected_layer = arcpy.management.SelectLayerByAttribute(params[2].valueAsText, "NEW_SELECTION",query)
                selected_count = int(arcpy.management.GetCount(selected_layer).getOutput(0))

                if selected_count > 0:
                    arcpy.CreateRandomPoints_management(workspace_path, "randPoint", selected_layer, "", 1)
                    
                    with arcpy.da.SearchCursor("randPoint", ["SHAPE@XY"]) as cursor:
                        for row in cursor:
                            # extract the x and y coordinates
                            x, y = row[0]
                else:
                    x, y = ["",""]

            excel_to_pd.at[i, "Lon(X)"] = x
            excel_to_pd.at[i, "Lat(Y)"] = y

            test_value = district

        arcpy.management.SelectLayerByAttribute(params[2].valueAsText, "CLEAR_SELECTION")

        # save the modified DataFrame back to the Excel file
        excel_to_pd.to_excel(params[0].valueAsText, index=False)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and 
        added to the display."""
        return

#============================================VIRUS MAPPING===================================================

class VirusMapping(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Virus Mapping"
        self.description = "Virus mappping is based on the Random point generator tool which generates random points within a certain polygon boundary based on an input linelist in .xls, .xlsx, and .csv and updates an output Masterlist of viruses"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        excel_file = arcpy.Parameter(name="excel_file",
                                     displayName="Excel File",
                                     direction="Input",
                                     datatype="DEFile",
                                     parameterType="Required")
        
        excel_file.filter.list = ['xls', 'xlsx', 'csv']
        
        field_name = arcpy.Parameter(name="field_name",
                                     displayName="Unique ID",
                                     direction="Input",
                                     datatype="GPString",
                                     parameterType="Required")
        
        admin_layer = arcpy.Parameter(name="admin_layer",
                                     displayName="Admin Layer",
                                     direction="Input",
                                     datatype="GPFeatureLayer",
                                     parameterType="Required")
        
        admin_field_name = arcpy.Parameter(name="admin_field_name",
                                     displayName="Unique ID",
                                     direction="Input",
                                     datatype="GPString",
                                     parameterType="Required")

        virus_master_list = arcpy.Parameter(name="virus_master_list",
                                     displayName="Virus Master List",
                                     direction="Input",
                                     datatype="GPFeatureLayer",
                                     parameterType="Required")
        
        try:
            # get the current map
            mxd = arcpy.mp.ArcGISProject("CURRENT")
            map = mxd.activeMap

            # get a list of layer objects in the map
            layers = map.listLayers()

            # add the layer names to the parameter's value list
            value_list = [layer.name for layer in layers]
            admin_layer.filter.list = value_list
        except:
            pass
        
        params = [excel_file, field_name, admin_layer, admin_field_name, virus_master_list]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, params):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if params[0].valueAsText:
            if params[0].valueAsText.split("\\")[-1].endswith(".csv"):
                excel_to_pd = pd.read_csv(params[0].valueAsText)
            else:
                excel_to_pd = pd.read_excel(params[0].valueAsText)
            
        columns = excel_to_pd.columns
        params[1].filter.list = sorted(columns.tolist())

        if params[2].valueAsText:
            field_objects = arcpy.ListFields(params[2].valueAsText)
            field_names = [field.name for field in field_objects]
            params[3].filter.list = sorted(field_names)

        return excel_to_pd

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, params, messages):
        """The source code of the tool."""
        #select by attribute of admin feature to generate point within
        if params[0].valueAsText.split("\\")[-1].endswith(".csv"):
            excel_to_pd = pd.read_csv(params[0].valueAsText)
        else:
            excel_to_pd = pd.read_excel(params[0].valueAsText)

        excel_to_pd["Lon(X)"] = ""
        excel_to_pd["Lat(Y)"] = ""

        input_fields = params[1].valueAsText
        admin_fields = params[3].valueAsText
        
        excel_to_pd.sort_values(by=input_fields)
        #admin_values = sorted(excel_to_pd[admin_field].tolist())
        selected_layer = ""
        test_value = "" #value used to test if the previously selected admin is not equal to the new
        for i, row in excel_to_pd.iterrows():
            admin_2_code = row[input_fields]
            #province = row[input_fields[1]]
            #district = row[input_fields[2]]
            
            if test_value == admin_2_code:
                selected_count = int(arcpy.management.GetCount(selected_layer).getOutput(0))

                if selected_count > 0:
                    arcpy.CreateRandomPoints_management(workspace_path, "randPoint", selected_layer, "", 1)
                    
                    with arcpy.da.SearchCursor("randPoint", ["SHAPE@XY"]) as cursor:
                        for row in cursor:
                            # extract the x and y coordinates
                            x, y = row[0]
                else:
                    x, y = ["",""]
            else:
                #arcpy.AddMessage(admin_field)
                #arcpy.AddMessage(admin_value)
                query = f"{admin_fields} = '{admin_2_code}'"
                #arcpy.AddMessage(query)
                selected_layer = arcpy.management.SelectLayerByAttribute(params[2].valueAsText, "NEW_SELECTION",query)
                selected_count = int(arcpy.management.GetCount(selected_layer).getOutput(0))

                if selected_count > 0:
                    arcpy.CreateRandomPoints_management(workspace_path, "randPoint", selected_layer, "", 1)
                    
                    with arcpy.da.SearchCursor("randPoint", ["SHAPE@XY"]) as cursor:
                        for row in cursor:
                            # extract the x and y coordinates
                            x, y = row[0]
                else:
                    x, y = ["",""]

            excel_to_pd.at[i, "Lon(X)"] = x
            excel_to_pd.at[i, "Lat(Y)"] = y

            test_value = admin_2_code

        arcpy.management.SelectLayerByAttribute(params[2].valueAsText, "CLEAR_SELECTION")

        # Define the spatial reference for the new features
        fields_to_update = ["Country","Province", "District", "EPID", "Emergence", "VirusType", "NT_Change", "DONSET", "WeekNo", "Source","SHAPE@XY"]

        virus_master_list = params[4].ValueAsText
        #arcpy.AddMessage(virus_master_list)

        # get EPID codes of the feature class as a list to be used for checking
        epid_codes = []
        # Use a SearchCursor to iterate through each row in the feature class
        with arcpy.da.SearchCursor(virus_master_list, ["EPID"]) as cursor:
            for row in cursor:
                # Append the values of the desired fields to the list
                epid_codes.append(row[0])

        no_coordinates = []
        already_in_db = []

        with arcpy.da.InsertCursor(virus_master_list, fields_to_update) as cursor:

            for index, row in excel_to_pd.iterrows():
                #arcpy.AddMessage("{},{},{},{},{}".format(row["Country"], row["Province"], row["District"],row["Lon(X)"], row["Lat(Y)"]))
                if row["Lon(X)"] != "":
                    if row["EPID_Number"] not in epid_codes:
                        new_feature = ((row["Country"], row["Province"], row["District"], row["EPID_Number"], row["ClusterLineage"], row["WPV_VDPV_Category"], row["NucleotideDifference_SABIN"], row["OnsetDate"], row["Week_Num"], row["Source_Case_ENV_Contact_HC"],  (row["Lon(X)"], row["Lat(Y)"])))
                        cursor.insertRow(new_feature)
                    else:
                        already_in_db.append(row["EPID_Number"])
                else:
                    no_coordinates.append(row["EPID_Number"])
        if len(no_coordinates) > 0:
            arcpy.AddMessage("No Coordinates found for the following Viruses \n{}\n".format(no_coordinates))

        if len(already_in_db) > 0:
            arcpy.AddMessage("The following Viruses where not added to the database because they already exist \n{}".format(already_in_db))

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and 
        added to the display."""
        return

#=============================================ODK Connector==================================================

class OnaConnector(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "ONA Connector"
        self.description = "Connects and retrieves data from the ONA server"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        # User name
        user = arcpy.Parameter(
                displayName="User Name",
                name="user_name",
                datatype="GPString",
                parameterType="Optional",
                direction="Input")
        
        # password
        password = arcpy.Parameter(
                displayName="Password",
                name="password",
                datatype="GPEncryptedString",
                parameterType="Optional",
                direction="Input")
        
        # url
        url = arcpy.Parameter(
                displayName="Url",
                name="url",
                datatype="GPString",
                parameterType="Optional",
                direction="Input")

        # project
        project = arcpy.Parameter(
                displayName="Project",
                name="project",
                datatype="GPString",
                parameterType="Optional",
                direction="Input",
                multiValue="True")
        
        # form
        form = arcpy.Parameter(
                displayName="Form",
                name="form",
                datatype="GPString",
                parameterType="Optional",
                direction="Input",
                multiValue="True")
        
        # Output layer
        output_layer = arcpy.Parameter(
                displayName="Output Layer",
                name="output_layer",
                datatype="GPFeatureLayer",
                parameterType="Optional",
                direction="Output")
        
        params = [user, password, url, project, form, output_layer]

        # set values
        #params[0].value = ""
        #params[1].value = ""
        params[2].value = "https://api.whonghub.org/"
        params[5].value = os.path.join(workspace_path, "output")
        #params[3].filter.list = ['whoalgeria', 'whomauritius', 'whozimbabwe', 'whoeswatini', 'whobenin', 'whoseychelles', 'whosierraleone', 'whoeritrea', 'whoburkinafaso', 'whocapeverde', 'whomozambique', 'whoburundi', 'whochad', 'ugandasuper', 'whomalawi', 'wholesotho', 'whostp', 'whosenegal', 'whomadagascar', 'ugandasuper', 'whoguinea', 'whoabidjan', 'whomauritania', 'who_gambia', 'whogabon', 'whocomoros', 'partners', 'whoalgeria', 'whocomoros', 'wholiberia', 'whoangola', 'whokenya', 'whomali', 'whocar', 'whosouthsudan', 'whosouthafrica', 'whocongo', 'whozambia', 'gis_blueline', 'who_gambia', 'whobissauguinea', 'whomozambique', 'whorwanda', 'whoangola', 'whosouthsudan', 'whomauritania', 'whosierraleone', 'whocameroon', 'whonamibia', 'whoguinea', 'whomali', 'whoburkinafaso', 'whobotswana', 'whokenya', 'gis_blueline', 'whogabon', 'whochad', 'whoethiopia', 'whoequaguinea', 'whomadagascar', 'who_tanzania', 'omsdrc', 'whozambia', 'whobenin', 'whocar', 'wholiberia', 'who_tanzania', 'whoethiopia', 'whotogo', 'omsniger', 'whoabidjan', 'whocongo', 'whoburundi', 'whoghana', 'whosenegal', 'whomalawi', 'whocameroon']

        #arcpy.AddMessage(params[2])
        
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, params):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        user = params[0].valueAsText
        password = params[1].valueAsText
        url = params[2].valueAsText
        #arcpy.AddMessage(url)
        # create the Ona instance
        if (user != None and password != None and url != None):
            global ona
            global projects
            params[3].filter.list = []
            ona = Ona(user, password, url)
            projects = ona.project() # get list and IDs of projects
            arcpy.AddMessage(projects)
            params[3].filter.list = sorted(list(projects.keys()))

        if (params[3].valueAsText != None):
            global forms
            params[4].filter.list = []
            project_id = projects[params[3].valueAsText]
            forms = ona.formList(project_id) # get list and IDs of projects
            #arcpy.AddMessage(forms)
            params[4].filter.list = sorted(list(forms.keys()))
        
        #if params[4].valueAsText != None:
            #params[5].value = os.path.join(workspace_path, params[4].valueAsText[1:6])

        #project_id = "project_id" # ID of project dervived from the selected project

        #form = ona.formList(project_id) # get list and IDs of forms

        return

    def updateMessages(self, params):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        """ # Getting getting the form id to be passed as input into the formdata method of the ona object.
        if params[4].valueAsText:
            if " " in params[4].valueAsText: #checing if there are spaces in the name of the input form name and removes the extra double quotations added by python
                form_id = forms[params[4].valueAsText[1:-1]]
            else:
                form_id = forms[params[4].valueAsText]
            # request the data from the server
            data = ona.formData(form_id)
            # pass the data to a pandas dataframe
            global df
            global cols
            df = pd.DataFrame(data)
            cols = "_geolocation" in df.columns

            if not cols:
                params[4].setErrorMessage("Selected form does not have geocoordinates. Please try another form.") """

        return

    def execute(self, params, messages):
        """The source code of the tool."""
        # Getting getting the form id to be passed as input into the formdata method of the ona object.
        if " " in params[4].valueAsText: #checing if there are spaces in the name of the input form name and removes the extra double quotations added by python
            form_id = forms[params[4].valueAsText[1:-1]]
        else:
            form_id = forms[params[4].valueAsText]
        # request the data from the server
        data = ona.formData(form_id)
        # pass the data to a pandas dataframe
        df = pd.DataFrame(data)
        #arcpy.AddMessage(df.columns)

        try:
            if "_geolocation" in df.columns:
                arcpy.AddMessage(type(df["_geolocation"][0]))
                if df["_geolocation"][0][0] != "[None,None]":
                    df[["Lon", "Lat"]] = pd.DataFrame(df._geolocation.tolist(), index= df.index) # spliting the geometry column to lon lat columns
                    # Changing from pandas dataframe to the esri spatial enabled dataframe
                    sdf = pd.DataFrame.spatial.from_xy(df, "Lat", "Lon", sr=4326)
                    # Saving the results of the sdf to a feature class
                    feature_class = arcpy.management.CopyFeatures(sdf, params[5].valueAsText)
                    # Get a reference to the current map
                    aprx = arcpy.mp.ArcGISProject("CURRENT")
                    map = aprx.activeMap
                    # Add the feature class to the map
                    map.addDataFromPath(feature_class)
                    #map.addLayer(feature_class)
                else:
                    table_data = arcpy.conversion.TableToTable(df, workspace_path, params[5].valueAsText.split("\\")[-1])
                    # Get a reference to the current map
                    aprx = arcpy.mp.ArcGISProject("CURRENT")
                    map = aprx.activeMap
                    # Add the feature class to the map
                    map.addDataFromPath(table_data)
            else:
                table_data = arcpy.conversion.TableToTable(df, workspace_path, params[5].valueAsText.split("\\")[-1])
                # Get a reference to the current map
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                map = aprx.activeMap
                # Add the feature class to the map
                map.addDataFromPath(table_data)
        except Exception as e:
            arcpy.AddMessage("Processing failed with the following exception : \n{}".format(e))

        return

    def postExecute(self, params):
        """This method takes place after outputs are processed and
        added to the display."""
        return


#======================================Backup Code===============================================================================================
class VirusMappingCPD(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Virus Mapping CPD"
        self.description = "Virus mappping is based on the Random point generator tool which generates random points within a certain polygon boundary based on an input linelist in .xls, .xlsx, and .csv and updates an output Masterlist of viruses"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        excel_file = arcpy.Parameter(name="excel_file",
                                     displayName="Excel File",
                                     direction="Input",
                                     datatype="DEFile",
                                     parameterType="Required")
        
        excel_file.filter.list = ['xls', 'xlsx', 'csv']
        
        field_name = arcpy.Parameter(name="field_name",
                                     displayName="Field Name",
                                     direction="Input",
                                     datatype="GPString",
                                     parameterType="Required",
                                     multiValue="True")
        
        admin_layer = arcpy.Parameter(name="admin_layer",
                                     displayName="Admin Layer",
                                     direction="Input",
                                     datatype="GPFeatureLayer",
                                     parameterType="Required")
        
        admin_field_name = arcpy.Parameter(name="admin_field_name",
                                     displayName="Admin Field Name",
                                     direction="Input",
                                     datatype="GPString",
                                     parameterType="Required",
                                     multiValue="True")

        virus_master_list = arcpy.Parameter(name="virus_master_list",
                                     displayName="Virus Master List",
                                     direction="Input",
                                     datatype="GPFeatureLayer",
                                     parameterType="Required")
        
        """ sql_clause = arcpy.Parameter(name="SQL",
                                     displayName="SQL",
                                     direction="Input",
                                     datatype="GPSQLExpression",
                                     parameterType="Required") """
        try:
            # get the current map
            mxd = arcpy.mp.ArcGISProject("CURRENT")
            map = mxd.activeMap

            # get a list of layer objects in the map
            layers = map.listLayers()

            # add the layer names to the parameter's value list
            value_list = [layer.name for layer in layers]
            admin_layer.filter.list = value_list
        except:
            pass
        
        params = [excel_file, field_name, admin_layer, admin_field_name, virus_master_list]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, params):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if params[0].valueAsText:
            if params[0].valueAsText.split("\\")[-1].endswith(".csv"):
                excel_to_pd = pd.read_csv(params[0].valueAsText)
            else:
                excel_to_pd = pd.read_excel(params[0].valueAsText)
            
        columns = excel_to_pd.columns
        params[1].filter.list = sorted(columns.tolist())

        if params[2].valueAsText:
            field_objects = arcpy.ListFields(params[2].valueAsText)
            field_names = [field.name for field in field_objects]
            params[3].filter.list = sorted(field_names)

        return excel_to_pd

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, params, messages):
        """The source code of the tool."""
        #select by attribute of admin feature to generate point within
        if params[0].valueAsText.split("\\")[-1].endswith(".csv"):
            excel_to_pd = pd.read_csv(params[0].valueAsText)
        else:
            excel_to_pd = pd.read_excel(params[0].valueAsText)

        excel_to_pd["Lon(X)"] = ""
        excel_to_pd["Lat(Y)"] = ""

        input_fields = params[1].valueAsText.split(";")
        admin_fields = params[3].valueAsText.split(";")
        
        excel_to_pd.sort_values(by=input_fields[2])
        #admin_values = sorted(excel_to_pd[admin_field].tolist())
        selected_layer = ""
        test_value = "" #value used to test if the previously selected admin is not equal to the new
        for i, row in excel_to_pd.iterrows():
            country = row[input_fields[0]]
            province = row[input_fields[1]]
            district = row[input_fields[2]]
            
            if test_value == district:
                selected_count = int(arcpy.management.GetCount(selected_layer).getOutput(0))

                if selected_count > 0:
                    arcpy.CreateRandomPoints_management(workspace_path, "randPoint", selected_layer, "", 1)
                    
                    with arcpy.da.SearchCursor("randPoint", ["SHAPE@XY"]) as cursor:
                        for row in cursor:
                            # extract the x and y coordinates
                            x, y = row[0]
                else:
                    x, y = ["",""]
            else:
                #arcpy.AddMessage(admin_field)
                #arcpy.AddMessage(admin_value)
                query = f"{admin_fields[0]} = '{country}' And {admin_fields[1]} = '{province}' And {admin_fields[2]} = '{district}'"
                #arcpy.AddMessage(query)
                selected_layer = arcpy.management.SelectLayerByAttribute(params[2].valueAsText, "NEW_SELECTION",query)
                selected_count = int(arcpy.management.GetCount(selected_layer).getOutput(0))

                if selected_count > 0:
                    arcpy.CreateRandomPoints_management(workspace_path, "randPoint", selected_layer, "", 1)
                    
                    with arcpy.da.SearchCursor("randPoint", ["SHAPE@XY"]) as cursor:
                        for row in cursor:
                            # extract the x and y coordinates
                            x, y = row[0]
                else:
                    x, y = ["",""]

            excel_to_pd.at[i, "Lon(X)"] = x
            excel_to_pd.at[i, "Lat(Y)"] = y

            test_value = district

        arcpy.management.SelectLayerByAttribute(params[2].valueAsText, "CLEAR_SELECTION")

        # Define the spatial reference for the new features
        fields_to_update = ["Country","Province", "District", "EPID", "Emergence", "VirusType", "NT_Change", "DONSET", "WeekNo", "Source","SHAPE@XY"]

        virus_master_list = params[4].ValueAsText
        #arcpy.AddMessage(virus_master_list)

        # get EPID codes of the feature class as a list to be used for checking
        epid_codes = []
        # Use a SearchCursor to iterate through each row in the feature class
        with arcpy.da.SearchCursor(virus_master_list, ["EPID"]) as cursor:
            for row in cursor:
                # Append the values of the desired fields to the list
                epid_codes.append(row[0])

        no_coordinates = []
        already_in_db = []

        with arcpy.da.InsertCursor(virus_master_list, fields_to_update) as cursor:

            for index, row in excel_to_pd.iterrows():
                #arcpy.AddMessage("{},{},{},{},{}".format(row["Country"], row["Province"], row["District"],row["Lon(X)"], row["Lat(Y)"]))
                if row["Lon(X)"] != "":
                    if row["EPID_Number"] not in epid_codes:
                        new_feature = ((row["Country"], row["Province"], row["District"], row["EPID_Number"], row["ClusterLineage"], row["WPV_VDPV_Category"], row["NucleotideDifference_SABIN"], row["OnsetDate"], row["Week_Num"], row["Source_Case_ENV_Contact_HC"],  (row["Lon(X)"], row["Lat(Y)"])))
                        cursor.insertRow(new_feature)
                    else:
                        already_in_db.append(row["EPID_Number"])
                else:
                    no_coordinates.append(row["EPID_Number"])
        if len(no_coordinates) > 0:
            arcpy.AddMessage("No Coordinates found for the following Viruses \n{}\n".format(no_coordinates))

        if len(already_in_db) > 0:
            arcpy.AddMessage("The following Viruses where not added to the database because they already exist \n{}".format(already_in_db))

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and 
        added to the display."""
        return