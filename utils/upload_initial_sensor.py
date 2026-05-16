from aas_python_http_client import ApiClient, Configuration, AssetAdministrationShellRepositoryAPIApi, \
    SubmodelRepositoryAPIApi
from aas_python_http_client.util import string_to_base64url
from basyx.aas import model
from basyx.aas.model import AssetInformation, AssetAdministrationShell, Submodel

# ─────────────────────────────────────────────
# Konfiguration: Server-Verbindung
# ─────────────────────────────────────────────
configuration = Configuration()
configuration.host = "http://192.168.1.101:8081"

api_client = ApiClient(configuration=configuration)
aas_repo_client = AssetAdministrationShellRepositoryAPIApi(api_client=api_client)
submodel_repo_client = SubmodelRepositoryAPIApi(api_client=api_client)

# ─────────────────────────────────────────────
# Schritt 1: Objekte erstellen
# ─────────────────────────────────────────────
asset_information = AssetInformation(
    asset_kind=model.AssetKind.INSTANCE,
    global_asset_id='http://example.com/asset/monitoring'
)


# ─────────────────────────────────────────────
# Schritt 2.1: Submodel erstellen
# ─────────────────────────────────────────────

submodel = Submodel(
    id_="http://example.com/submodel/monitoring",
    id_short="EnergyMonitoring")

# ─────────────────────────────────────────────
# Schritt 2.2: Properties erstellen
# ─────────────────────────────────────────────

property_monitoring0 = model.Property(
    id_short="sensorvalue0",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/engergy-monitoring'
    ),)
))

property_monitoring1 = model.Property(
    id_short="sensorvalue1",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/engergy-monitoring'
    ),)
))

property_monitoring2 = model.Property(
    id_short="sensorvalue2",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/engergy-monitoring'
    ),)
))

property_monitoring3 = model.Property(
    id_short="sensorvalue3",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/engergy-monitoring'
    ),)
))

property_monitoring4 = model.Property(
    id_short="sensorvalue4",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/engergy-monitoring'
    ),)
))

property_monitoring5 = model.Property(
    id_short="sensorvalue5",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/engergy-monitoring'
    ),)
))

property_monitoring6 = model.Property(
    id_short="sensorvalue6",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/engergy-monitoring'
    ),)
))

property_monitoring7 = model.Property(
    id_short="sensorvalue7",
    value_type=model.datatypes.Float, 
    value=0.0,
    semantic_id=model.ExternalReference(
    (model.Key(
        type_=model.KeyTypes.GLOBAL_REFERENCE,
        value='https://example.org/engergy-monitoring'
    ),)
))

# ─────────────────────────────────────────────
# Schritt 2.3: Submodel mit Properties verknüpfen
# ─────────────────────────────────────────────
submodel.submodel_element.add(property_monitoring0)
submodel.submodel_element.add(property_monitoring1)
submodel.submodel_element.add(property_monitoring2)
submodel.submodel_element.add(property_monitoring3)
submodel.submodel_element.add(property_monitoring4)
submodel.submodel_element.add(property_monitoring5)
submodel.submodel_element.add(property_monitoring6)
submodel.submodel_element.add(property_monitoring7)


# ─────────────────────────────────────────────
# Schritt 2.4: shell
# ─────────────────────────────────────────────
aas = AssetAdministrationShell(
    id_="http://example.com/aas/monitoring",
    id_short="MonitoringAAS",
    asset_information=asset_information,
    submodel={model.ModelReference.from_referable(submodel)}
)


# ─────────────────────────────────────────────
# S1hritt 3: Submodel auf Server hochladen
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