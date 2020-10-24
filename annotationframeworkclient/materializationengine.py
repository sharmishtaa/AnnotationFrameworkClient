from .base import ClientBaseWithDataset, ClientBaseWithDatastack, ClientBase, _api_versions, _api_endpoints
from .auth import AuthClient
from .endpoints import annotation_common, annotation_api_versions
from .infoservice import InfoServiceClientV2
import requests
import time
import json 
import numpy as np
from datetime import date, datetime

SERVER_KEY = "me_server_address"

class MEEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.uint64):
            return int(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def MaterializationClient(server_address,
                          datastack_name=None,
                          auth_client=None,
                          api_version='latest'):
    """ Factory for returning AnnotationClient
    Parameters
    ----------
    server_address : str 
        server_address to use to connect to (i.e. https://minniev1.microns-daf.com)
    datastack_name : str
        Name of the datastack.
    auth_client : AuthClient or None, optional
        Authentication client to use to connect to server. If None, do not use authentication.
    api_version : str or int (default: latest)
        What version of the api to use, 0: Legacy client (i.e www.dynamicannotationframework.com) 
        2: new api version, (i.e. minniev1.microns-daf.com)
        'latest': default to the most recent (current 2)

    Returns
    -------
    ClientBaseWithDatastack
        List of datastack names for available datastacks on the annotation engine
    """

    if auth_client is None:
        auth_client = AuthClient()

    auth_header = auth_client.request_header
    endpoints, api_version = _api_endpoints(api_version, SERVER_KEY, server_address,
                                            annotation_common, annotation_api_versions, auth_header)
    

    AnnoClient = client_mapping[api_version]
    if api_version>1:
        return AnnoClient(server_address, auth_header, api_version,
                          endpoints, SERVER_KEY, aligned_volume_name)
    else:
        return AnnoClient(server_address, auth_header, api_version,
                          endpoints, SERVER_KEY, dataset_name)



class MaterializatonClient(ClientBase):
    def __init__(self, server_address, auth_header, api_version,
                 endpoints, server_name, datastack_name, version=None):
        super(AnnotationClientV2, self).__init__(server_address,
                                               auth_header, api_version, endpoints, server_name)
                                         
        self._datastack_name = datastack_name
        self._version = self.most_recent_version()

    @property
    def datastack_name(self):
        return self._datastack_name

    @property
    def version(self):
        return self._version
    
    def most_recent_version(self, datastack_name=None):
        """get the most recent version of materialization 
        for this datastack name

        Args:
            datastack_name (str, optional): datastack name to find most
            recent materialization of. 
            If None, uses the one specified in the client.
        """

    def get_tables(self, datastack_name=None, version=None):
        """ Gets a list of table names for a datastack

        Parameters
        ----------
        datastack_name : str or None, optional
            Name of the datastack, by default None.
            If None, uses the one specified in the client.
            Will be set correctly if you are using the framework_client
        version: int or None, optional
            the version to query, else get the tables in the most recent version
        Returns
        -------
        list
            List of table names
        """
        if datastack_name is None:
            datastack_name = self.datastack_name
        endpoint_mapping = self.default_url_mapping
        endpoint_mapping["datastack_name"] = datastack_name
        # TODO fix up latest version
        url = self._endpoints["tables"].format_map(endpoint_mapping)

        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_annotation_count(self, table_name:str,
                             datastack_name=None,
                             version=None):
        """ Get number of annotations in a table

        Parameters
        ----------
        table_name (str): 
            name of table to mark for deletion
        aligned_volume_name: str or None, optional,
            Name of the aligned_volume. If None, uses the one specified in the client.
        version: int or None, optional
            the version to query, else get the tables in the most recent version
        Returns
        -------
        int
            number of annotations
        """
        if aligned_volume_name is None:
            aligned_volume_name = self.aligned_volume_name

        endpoint_mapping = self.default_url_mapping
        endpoint_mapping["aligned_volume_name"] = aligned_volume_name
        endpoint_mapping["table_name"] = table_name

        url = self._endpoints["table_count"].format_map(endpoint_mapping)

        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_table_metadata(self, table_name:str, datastack_name=None):
        """ Get metadata about a table

        Parameters
        ----------
        table_name (str): 
            name of table to mark for deletion
        datastack_name: str or None, optional,
            Name of the datastack_name.
            If None, uses the one specified in the client.


        Returns
        -------
        json
            metadata about table
        """
        if aligned_volume_name is None:
            aligned_volume_name = self.aligned_volume_name

        endpoint_mapping = self.default_url_mapping
        endpoint_mapping["aligned_volume_name"] = aligned_volume_name
        endpoint_mapping["table_name"] = table_name

        url = self._endpoints["table_info"].format_map(endpoint_mapping)

        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_annotation(self, table_name, annotation_ids,
                       materialization_version=None,
                       datastack_name=None):
        """ Retrieve an annotation or annotations by id(s) and table name.

        Parameters
        ----------
        table_name : str
            Name of the table
        annotation_ids : int or iterable
            ID or IDS of the annotation to retreive
        materialization_version: int or None
            materialization version to use
            If None, uses the one specified in the client
        datastack_name : str or None, optional
            Name of the datastack_name.
            If None, uses the one specified in the client.
        Returns
        -------
        list
            Annotation data
        """
        if materialization_version is None:
            materialization_version = self.version
        if datastack_name is None:
            datastack_name = self.datastack_name

        endpoint_mapping = self.default_url_mapping
        endpoint_mapping["datastack_name"] = datastack_name
        endpoint_mapping["table_name"] = table_name
        endpoint_mapping["version"] = materialization_version
        url = self._endpoints["annotations"].format_map(endpoint_mapping)
        try:
            iter(annotation_ids)
        except TypeError:
            annotation_ids = [annotation_ids]

        params = {
            'annotation_ids': ",".join([str(a) for a in annotation_ids])
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def query_table(self, 
                    tables,
                    filter_in_dict=None,
                    filter_out_dict=None,
                    filter_equal_dict=None,
                    filter_spatial=None,
                    join_args=None,
                    select_columns=None,
                    offset = None,
                    datastack_name=None,
                    materialization_version=None):
        """generic query on materialization tables

        Args:
            tables: list of lists
                standard: list of one entry: table_name of table that one wants to
                        query
                join: list of two lists: first entries are table names, second
                                        entries are the columns used for the join
            filter_in_dict (dict of dicts, optional): 
                outer layer: keys are table names
                inner layer: keys are column names, values are allowed entries.
                Defaults to None.
            filter_out_dict (dict of dicts, optional): 
                outer layer: keys are table names
                inner layer: keys are column names, values are not allowed entries.
                Defaults to None.
            filter_equal_dict (dict of dicts, optional): 
                outer layer: keys are table names
                inner layer: keys are column names, values are specified entry.
                Defaults to None.
            select_columns (list of str, optional): columns to select. Defaults to None.
            offset (int, optional): result offset to use. Defaults to None.
                will only return top K results. 
            datastack_name (str, optional): datastack to query. 
                If None defaults to one specified in client. 
            materialization_version (int, optional): version to query. 
                If None defaults to one specified in client.
        Returns:
        pd.DataFrame: a pandas dataframe of results of query

        """
        if materialization_version is None:
            materialization_version = self.version
        if datastack_name is None:
            datastack_name = self.datastack_name

        endpoint_mapping = self.default_url_mapping
        endpoint_mapping["datastack_name"] = datastack_name
        endpoint_mapping["version"] = materialization_version
        data = {}
        query_args = {}
        if len(tables)==1:
            assert(type(tables[0])==str)
            endpoint_mapping["table_name"] = tables[0]
            single_table=True
            url = self._endpoints["simple_query"].format_map(endpoint_mapping)
        else:
            single_table=False
            data['tables']=tables
            url = self._endpoints["join_query"].format_map(endpoint_mapping)
        
        if filter_in_dict is not None:
            data['filter_in_dict']=filter_in_dict
        if filter_out_dict is not None:
            data['filter_out_dict']=filter_out_dict
        if filter_equal_dict is not None:
            data['filter_out_dict']=filter_equal_dict
        if select_columns is not None:
            data['select_columns']=select_columns
        if offset is not None:
            query_args['offset']=offset

        r = self.session.post(url, data = json.dumps(data, cls=MEEncoder),
                              params=query_params)
                              
client_mapping = {1: MaterializationClient,
                  'latest': MaterializationClient}