import requests
import arcpy
from arcgis.features import GeoAccessor, GeoSeriesAccessor
import pandas as pd
"""
Create ODK Classes and methods to pull data from ODK base server
"""
arcpy.env.overwriteOutput = True
class Connection:
    def __init__(self, user:str, password:str, url:str):
        self.user = user
        self.password = password
        self.url = url
    
    def testConnection(self):
        try:
            rq = requests.get(self.url, auth=(self.user, self.password))
            
            return [rq.status_code, rq.json()] #change this to return the consction status and the domain of the url
        except Exception as e:
            return e
    
    def domainName(self):
        domain_name = self.url.split("/")[2]
        
        return domain_name
    
    def project(self):
        pass
    
    def formList(self):
        pass
    
    def formData(self):
        pass

#Ona server class

class Ona(Connection):
    
    def project(self): # method that returns the list of dict [{"projectid" : "owner"}] of all projects available for the user credentials.
        project_url = "https://" + self.domainName() + "/api/v1/projects"
        #print(project_url)
        data = requests.get(project_url, auth=(self.user, self.password)).json()
        projects = {}
        #project_instance = {}
        
        for project in data:
            projects[project["owner"].split("/")[-1]] = project["projectid"]
            #projects.append(project_instance)
            
            #project_instance = {}
        
        return projects
    
    def formList(self, project_id): # method that returns the list of dict [{"formid" : "form_name"}] of all Forms in a particular project, available for the user credentials.
        forms_url = "https://" + self.domainName() + "/api/v1/projects/" + str(project_id)
        data = requests.get(forms_url, auth=(self.user, self.password)).json()
        forms = {}
        #form_instance = {}
        
        for form in data["forms"]:
            forms[form["name"]] = form["formid"]
            #forms.append(form_instance)
            
            #form_instance = {}
            
        return forms
    
    def formData(self, form_id): # method that returns the list of dict [{}] of all data in a particular form or formid.
        form_data_url = "https://" + self.domainName() + "/api/v1/data/" + str(form_id) + ".json"
        data = requests.get(form_data_url, auth=(self.user, self.password)).json()
        
        return data

#Kobo server class

class Kobo(Connection):
    
    def projects(self):
        pass
    
    def formList(self, project_id):
        pass
    
    def formData(self, form_id):
        pass
    
#getODK server class

class GetODK(Connection):
    
    def projects(self):
        pass
    
    def formList(self, project_id):
        pass
    
    def formData(self, form_id):
        pass
"""
Create main function
"""
if __name__ == "__main__":
    
    data = Ona("gis_blueline", "G1sb!ue", "https://esurv.afro.who.int/api/v1/data/8604.json").formData(8604)
    #print(data)
    df = pd.DataFrame(data)
    columns = df.columns

    if "_geolocation" not in columns:
        print("_geolocation not in Columns")
    else:
        print("_geolocation in Columns")
    """ df = pd.DataFrame(data)
    df[["Lon", "Lat"]] = pd.DataFrame(df._geolocation.tolist(), index= df.index)
    #print(df["Lon"])
    sdf = pd.DataFrame.spatial.from_xy(df, "Lat", "Lon", sr=4326)
    #columns = df.columns.tolist()
    #print(columns)
    arcpy.management.CopyFeatures(sdf, 'D:/myfeatureclass.shp') """