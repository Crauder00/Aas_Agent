from aas_python_http_client import ApiClient, Configuration, AssetAdministrationShellRepositoryAPIApi, \
    SubmodelRepositoryAPIApi
from aas_python_http_client.util import string_to_base64url
from basyx.aas import model

configuration = Configuration()
configuration.host = "http://192.168.1.128:8081"

api_client = ApiClient(configuration=configuration)

aasRepoClient = AssetAdministrationShellRepositoryAPIApi(api_client=api_client)
submodelRepoClient = SubmodelRepositoryAPIApi(api_client=api_client)

# query all asset administration shells
# all_aas = aasRepoClient.get_all_asset_administration_shells()
# print(all_aas)


all_submodels = submodelRepoClient.get_all_submodels()
print(all_submodels)