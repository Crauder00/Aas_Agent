from aas_python_http_client import ApiClient, Configuration, AssetAdministrationShellRepositoryAPIApi, \
    SubmodelRepositoryAPIApi
from aas_python_http_client.util import string_to_base64url
from basyx.aas import model
from basyx.aas.model import AssetInformation, AssetAdministrationShell, Submodel

# ─────────────────────────────────────────────
# Konfiguration: Server-Verbindung
# ─────────────────────────────────────────────
configuration = Configuration()
configuration.host = "http://192.168.1.128:8081"

api_client = ApiClient(configuration=configuration)
aas_repo_client = AssetAdministrationShellRepositoryAPIApi(api_client=api_client)
submodel_repo_client = SubmodelRepositoryAPIApi(api_client=api_client)

# ─────────────────────────────────────────────
# Schritt 1: Objekte erstellen
# ─────────────────────────────────────────────
asset_information = AssetInformation(
    asset_kind=model.AssetKind.INSTANCE,
    global_asset_id='http://example.com/asset/productionmachine'
)


# ─────────────────────────────────────────────
# Schritt 2.1: Submodel erstellen
# ─────────────────────────────────────────────

submodel = Submodel(
    id_="http://example.com/submodel/carbonfootprint",
    id_short="CarbonFootprintSubmodel")

# ─────────────────────────────────────────────
# Schritt 2.2: Properties erstellen
# ─────────────────────────────────────────────

property_emissionfactor = model.Property(
    id_short="emissionfactor",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/ghg/scope2/emission-factor'
    ),)
))

list_scope2_emissions = model.SubmodelElementList(
    id_short='scope2emissionslist',
    type_value_list_element=model.Property,         
    value_type_list_element=model.datatypes.Float,  
    semantic_id=model.ExternalReference(
        (model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='https://example.org/ghg/scope2/list'
        ),)
    )
)

property_total_emissions = model.Property(
    id_short="totalemissions",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/ghg/total-emissions'
    ),)
))

property_scope3_proxy = model.Property(
    id_short="scope3proxy",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/ghg/scope3'
    ),)
))

property_resetaggregation = model.Property(
    id_short="resetaggregation",
    value_type=model.datatypes.Boolean, 
    value=False,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/ghg/scope2/aggregation/reset'
    ),)
))

property_triggeraggregation = model.Property(
    id_short="triggeraggregation",
    value_type=model.datatypes.Boolean, 
    value=False,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/ghg/scope2/aggregation/trigger'
    ),)
))

# ─────────────────────────────────────────────
# Schritt 2.3: Submodel mit Properties verknüpfen
# ─────────────────────────────────────────────
submodel.submodel_element.add(property_emissionfactor)
submodel.submodel_element.add(list_scope2_emissions)
submodel.submodel_element.add(property_total_emissions)
submodel.submodel_element.add(property_scope3_proxy)
submodel.submodel_element.add(property_resetaggregation)
submodel.submodel_element.add(property_triggeraggregation)

# ─────────────────────────────────────────────
# Schritt 2.4: shell
# ─────────────────────────────────────────────
aas = AssetAdministrationShell(
    id_="http://example.com/aas/productionmachine",
    id_short="ProductionMachineAAS",
    asset_information=asset_information,
    submodel={model.ModelReference.from_referable(submodel)}
)


# ─────────────────────────────────────────────
# Schritt 3: Submodel auf Server hochladen
# ─────────────────────────────────────────────
# Submodel ZUERST hochladen, da die AAS nur eine Referenz darauf enthält.
# Der Server muss das Submodel kennen, bevor die AAS darauf verweist.
print("Lade Submodel hoch...")
submodel_repo_client.post_submodel(submodel)
print(f"  ✓ Submodel '{submodel.id}' erfolgreich gespeichert.")


# ─────────────────────────────────────────────
# Schritt 4: AAS auf Server hochladen
# ─────────────────────────────────────────────
print("Lade AAS hoch...")
aas_repo_client.post_asset_administration_shell(aas)
print(f"  ✓ AAS '{aas.id}' erfolgreich gespeichert.")


# # ─────────────────────────────────────────────
# # Schritt 5: Verifikation – Objekte vom Server lesen
# # ─────────────────────────────────────────────
# print("\nVerifikation:")

# server_aas = aas_repo_client.get_asset_administration_shell_by_id(
#     string_to_base64url(aas.id)
# )
# print(f"  AAS vom Server:     {server_aas.id}")

# server_submodel = submodel_repo_client.get_submodel_by_id(
#     string_to_base64url(submodel.id)
# )


# print(f"  Submodel vom Server: {server_submodel.id}")
# print(f"  Property-Wert:       {server_submodel.submodel_element.get("id_short", "ExampleProperty")}")