from aas_python_http_client import ApiClient, Configuration, AssetAdministrationShellRepositoryAPIApi, \
    SubmodelRepositoryAPIApi
from basyx.aas import model
from basyx.aas.model import AssetInformation, AssetAdministrationShell, Submodel, MultiLanguageNameType

# ─────────────────────────────────────────────
# Konfiguration: Server-Verbindung
# ─────────────────────────────────────────────
configuration = Configuration()
configuration.host = "http://localhost:8081"

api_client = ApiClient(configuration=configuration)
aas_repo_client = AssetAdministrationShellRepositoryAPIApi(api_client=api_client)
submodel_repo_client = SubmodelRepositoryAPIApi(api_client=api_client)

# ─────────────────────────────────────────────
# Hilfsfunktion: Eine Station erstellen
# ─────────────────────────────────────────────
def create_station(station_number: int) -> model.SubmodelElementCollection:
    n = station_number

    prop_current_cf = model.Property(
        id_short="currentCFSubmodel",  # ← required (inside a collection)
        display_name=model.MultiLanguageNameType({"en": "currentCFSubmodel"}),
        value_type=model.datatypes.String,
        value="",
        semantic_id=model.ExternalReference(
            (model.Key(
                type_=model.KeyTypes.GLOBAL_REFERENCE,
                value='https://example.org/ghg/station/current-cf-submodel'
            ),)
        )
    )

    prop_trigger = model.Property(
        id_short="triggeraggregation",  # ← required (inside a collection)
        display_name=model.MultiLanguageNameType({"en": "triggeraggregation"}),
        value_type=model.datatypes.Boolean,
        value=False,
        semantic_id=model.ExternalReference(
            (model.Key(
                type_=model.KeyTypes.GLOBAL_REFERENCE,
                value='https://example.org/ghg/scope2/aggregation/trigger'
            ),)
        )
    )

    prop_reset = model.Property(
        id_short="resetaggregation",  # ← required (inside a collection)
        display_name=model.MultiLanguageNameType({"en": "resetaggregation"}),
        value_type=model.datatypes.Boolean,
        value=False,
        semantic_id=model.ExternalReference(
            (model.Key(
                type_=model.KeyTypes.GLOBAL_REFERENCE,
                value='https://example.org/ghg/scope2/aggregation/reset'
            ),)
        )
    )

    list_emissions = model.SubmodelElementList(
        id_short="scope2emissionslist",  # ← required (inside a collection)
        display_name=model.MultiLanguageNameType({"en": "scope2emissionslist"}),
        type_value_list_element=model.Property,
        value_type_list_element=model.datatypes.Float,
        semantic_id=model.ExternalReference(
            (model.Key(
                type_=model.KeyTypes.GLOBAL_REFERENCE,
                value='https://example.org/ghg/scope2/list'
            ),)
        )
    )

    error_message = model.Property(
        id_short="errorMessage",  # ← required (inside a collection)
        display_name=model.MultiLanguageNameType({"en": "errorMessage"}),
        value_type=model.datatypes.String,
        value="",
        semantic_id=model.ExternalReference(
            (model.Key(
                type_=model.KeyTypes.GLOBAL_REFERENCE,
                value='https://example.org/ghg/station/error-message'
            ),)
        )
    )

    station_collection = model.SubmodelElementCollection(
        id_short=None,  # ← must be None (direct child of a SubmodelElementList)
        display_name=model.MultiLanguageNameType({"en": f"Station {n}"}),
        value=[
            prop_current_cf,
            prop_trigger,
            prop_reset,
            list_emissions,
            error_message,
        ]
    )

    return station_collection


# ─────────────────────────────────────────────
# Schritt 1: Asset Information
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
    id_short="CFCalculationSubmodel"
)

# ─────────────────────────────────────────────
# Schritt 2.2: Globaler Emissionsfaktor
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
    )
)

# ─────────────────────────────────────────────
# Schritt 2.3: Stations-Liste mit 8 Stationen
# ─────────────────────────────────────────────
stations_list = model.SubmodelElementList(
    id_short="Stations",
    type_value_list_element=model.SubmodelElementCollection,
    semantic_id=model.ExternalReference(
        (model.Key(
            type_=model.KeyTypes.GLOBAL_REFERENCE,
            value='https://example.org/ghg/stations'
        ),)
    ),
    value=[create_station(i) for i in range(1, 9)]  # Station 1 bis 8
)

# ─────────────────────────────────────────────
# Schritt 2.4: Submodel zusammenbauen
# ─────────────────────────────────────────────
submodel.submodel_element.add(property_emissionfactor)
submodel.submodel_element.add(stations_list)

# ─────────────────────────────────────────────
# Schritt 2.5: AAS erstellen
# ─────────────────────────────────────────────
aas = AssetAdministrationShell(
    id_="http://example.com/aas/productionmachine",
    id_short="ProductionMachineAAS",
    asset_information=asset_information,
    submodel={model.ModelReference.from_referable(submodel)}
)

# ─────────────────────────────────────────────
# Schritt 3: Submodel hochladen
# ─────────────────────────────────────────────
print("Lade Submodel hoch...")
submodel_repo_client.post_submodel(submodel)
print(f"  ✓ Submodel '{submodel.id}' erfolgreich gespeichert.")

# ─────────────────────────────────────────────
# Schritt 4: AAS hochladen
# ─────────────────────────────────────────────
print("Lade AAS hoch...")
aas_repo_client.post_asset_administration_shell(aas)
print(f"  ✓ AAS '{aas.id}' erfolgreich gespeichert.")