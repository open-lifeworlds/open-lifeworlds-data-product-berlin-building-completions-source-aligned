import os

import pandas as pd

from lib.tracking_decorator import TrackingDecorator


@TrackingDecorator.track_time
def convert_data_to_csv(source_path, results_path, clean=False, quiet=False):
    # Iterate over files
    for subdir, dirs, files in sorted(os.walk(source_path)):

        # Make results path
        subdir = subdir.replace(f"{source_path}/", "")
        os.makedirs(os.path.join(results_path, subdir), exist_ok=True)

        for file_name in [file_name for file_name in sorted(files) if not file_name.startswith(f"~")]:
            source_file_path = os.path.join(source_path, subdir, file_name)
            convert_file_to_csv(source_file_path, clean=clean, quiet=quiet)
            convert_file_to_csv_by_type_and_contractor_including_measures_on_existing_buildings(source_file_path,
                                                                                                clean=clean,
                                                                                                quiet=quiet)


def convert_file_to_csv(source_file_path, clean=False, quiet=False):
    source_file_name, source_file_extension = os.path.splitext(source_file_path)
    file_path_csv = f"{source_file_name}.csv"

    # Check if result needs to be generated
    if clean or not os.path.exists(file_path_csv):
        # Determine engine
        if source_file_extension == ".xlsx":
            engine = "openpyxl"
        elif source_file_extension == ".xls":
            engine = None
        else:
            return

        year = os.path.basename(source_file_name).split(sep="-")[-2]

        try:
            dataframes = []

            # Iterate over sheets
            sheet = "Baufert. Tab. 1 u. 2"
            skiprows = 10
            names = ["year", "building_completion_total", "building_completion_residential_buildings",
                     "building_completion_non_residential_buildings",
                     "building_measure_on_existing_buildings", "usage_area", "living_area", "apartments",
                     "apartment_rooms", "total_costs"]
            drop_columns = []

            dataframe = pd.read_excel(source_file_path, engine=engine, sheet_name=sheet, skiprows=skiprows,
                                      usecols=list(range(0, len(names))), names=names) \
                .drop(columns=drop_columns, errors="ignore") \
                .dropna()
            dataframe = dataframe.loc[dataframe["year"] == int(year)].head(1)
            dataframes.append(dataframe)

            sheet = "Baufert. Tab. 1 u. 2"
            skiprows = 33
            names = ["year", "building_completions_new", "building_completions_new_with_1_apartment",
                     "building_completions_new_with_2_apartments",
                     "building_completions_new_with_3_or_more_apartment",
                     "building_completions_new_total_apartments", "building_completions_new_volume",
                     "building_completions_new_living_area", "building_completions_new_costs"]
            drop_columns = []
            dataframe = pd.read_excel(source_file_path, engine=engine, sheet_name=sheet, skiprows=skiprows,
                                      usecols=list(range(0, len(names))), names=names) \
                .drop(columns=drop_columns, errors="ignore") \
                .dropna()
            dataframe = dataframe.loc[dataframe["year"] == int(year)].head(1)
            dataframes.append(dataframe)

            # Join dataframes
            dataframe = pd.concat(dataframes, axis=1).drop(columns=["year"], errors="ignore")

            # Write csv file
            if dataframe.shape[0] > 0:
                dataframe.to_csv(file_path_csv, index=False)
            if not quiet:
                print(f"✓ Convert {os.path.basename(file_path_csv)}")
            else:
                if not quiet:
                    print(dataframe.head())
                    print(f"✗️ Empty {os.path.basename(file_path_csv)}")
        except Exception as e:
            print(f"✗️ Exception: {str(e)}")
    elif not quiet:
        print(f"✓ Already exists {os.path.basename(file_path_csv)}")


def convert_file_to_csv_by_type_and_contractor_including_measures_on_existing_buildings(source_file_path, clean=False,
                                                                                        quiet=False):
    source_file_name, source_file_extension = os.path.splitext(source_file_path)
    file_path_csv = f"{source_file_name}-3-by-type-and-constructor-including-measures-on-existing-buildings.csv"

    # Check if result needs to be generated
    if clean or not os.path.exists(file_path_csv):
        # Determine engine
        if source_file_extension == ".xlsx":
            engine = "openpyxl"
        elif source_file_extension == ".xls":
            engine = None
        else:
            return

        try:
            sheet = "Baufert. Tab. 3"
            skiprows = 7
            names = ["type", "measures", "usage_area", "apartments", "living_area", "living_rooms", "estimated_costs"]
            drop_columns = []

            dataframe = pd.read_excel(source_file_path, engine=engine, sheet_name=sheet, skiprows=skiprows,
                                      usecols=list(range(0, len(names))), names=names) \
                .drop(columns=drop_columns, errors="ignore") \
                .dropna() \
                .replace("–", 0) \
                .assign(type=lambda df: df["type"].apply(lambda row: build_type_name(row)))

            dataframe.reset_index(drop=True, inplace=True)
            dataframe = dataframe.assign(type_index=lambda df: df.index) \
                .assign(type_parent_index=lambda df: df.apply(lambda row: build_type_parent_index(row), axis=1)) \
                .fillna(-1) \
                .assign(type_parent_index=lambda df: df["type_parent_index"].astype(int))
            dataframe.insert(0, "type_index", dataframe.pop("type_index"))
            dataframe.insert(1, "type_parent_index", dataframe.pop("type_parent_index"))

            # Write csv file
            if dataframe.shape[0] > 0:
                dataframe.to_csv(file_path_csv, index=False)
            if not quiet:
                print(f"✓ Convert {os.path.basename(file_path_csv)}")
            else:
                if not quiet:
                    print(dataframe.head())
                    print(f"✗️ Empty {os.path.basename(file_path_csv)}")
        except Exception as e:
            print(f"✗️ Exception: {str(e)}")
    elif not quiet:
        print(f"✓ Already exists {os.path.basename(file_path_csv)}")


def build_type_index(row):
    return row.name


def build_type_name(value):
    value = value.lstrip().rstrip()

    if value == "Wohn- und Nichtwohngebäude":
        return "residential_and_non_residential_buildings"
    elif value == "Wohngebäude zusammen":
        return "residential_buildings"
    elif value == "Wohnheime":
        return "dormitories"
    elif value == "Wohngebäude mit Eigentumswohnungen":
        return "residential_buildings_with_condominium"
    elif value == "Öffentliche Bauherren":
        return "public_builders"
    elif value == "Unternehmen":
        return "companies"
    elif value == "Wohnungsunternehmen":
        return "housing_companies"
    elif value == "Immobilienfonds":
        return "real_estate_funds"
    elif value == "Land- und Forstw., Tierh., Fischerei":
        return "agriculture_forestry_animal_husbandry_fishing"
    elif value == "Produzierendes Gewerbe":
        return "manufacturing_industry"
    elif value.startswith("Handel, Kreditinst., Dienstleistung,"):
        return "trade_banking_services_insurance_transport_and_communications"
    elif value == "Private Haushalte":
        return "private_households"
    elif value == "Organisationen ohne Erwerbszweck":
        return "non_profit_organizations"
    elif value == "Nichtwohngebäude":
        return "non_residential_buildings"
    elif value == "Anstaltsgebäude":
        return "institution_buildings"
    elif value == "Büro- und Verwaltungsgebäude":
        return "office_and_administration_buildings"
    elif value == "Landwirtschaftliche Betriebsgebäude":
        return "algricultural_buildings"
    elif value == "Nichtlandwirtschaftliche Betriebsgebäude":
        return "non_algricultural_buildings"
    elif value == "Fabrik- und Werkstattgebäude":
        return "factory_and_workshop_buildings"
    elif value == "Handelsgebäude":
        return "commercial_buildings"
    elif value == "Warenlagergebäude":
        return "warehouse_buildings"
    elif value == "Hotels und Gaststätten":
        return "hotels_and_restaurants"
    elif value == "Sonstige Nichtwohngebäude":
        return "other_non_residential_buildings"
    elif value == "Ausgewählte Infrastrukturgebäude":
        return "selected_infrastructure_buildings"
    elif value == "Öffentliche Bauherren":
        return "public_building_owners"
    elif value == "Unternehmen":
        return "companies"
    elif value == "Wohnungsunternehmen":
        return "housing_companies"
    elif value == "Immobilienfonds":
        return "property_funds"
    elif value == "Land- und Forstw., Tierh., Fischerei":
        return "agriculture_forestry_animal_husbandry_fishing"
    elif value == "Produzierendes Gewerbe":
        return "manufacturing_industry"
    elif value == "Handel, Kreditinst., Dienstleistung,Versicherung, Verkehr u. Nachr.überm.":
        return "Trade_banking_services_insurance_transport_and_telecommunications"
    elif value == "Private Haushalte":
        return "private_households"
    elif value == "Organisationen o. Erwerbszweck":
        return "non_profit_organisations"
    else:
        return value


def build_type_parent_index(row):
    row_index = row.name

    if row_index == 0:
        return None
    elif row_index == 1:
        return 0
    elif row_index == 2:
        return 1
    elif row_index == 3:
        return 1
    elif row_index == 4:
        return 1
    elif row_index == 5:
        return 1
    elif row_index == 6:
        return 5
    elif row_index == 7:
        return 5
    elif row_index == 8:
        return 5
    elif row_index == 9:
        return 5
    elif row_index == 10:
        return 5
    elif row_index == 11:
        return 1
    elif row_index == 12:
        return 1
    elif row_index == 13:
        return 0
    elif row_index == 14:
        return 13
    elif row_index == 15:
        return 13
    elif row_index == 16:
        return 13
    elif row_index == 17:
        return 13
    elif row_index == 18:
        return 17
    elif row_index == 19:
        return 17
    elif row_index == 20:
        return 17
    elif row_index == 21:
        return 17
    elif row_index == 22:
        return 13
    elif row_index == 23:
        return 13
    elif row_index == 24:
        return 13
    elif row_index == 25:
        return 13
    elif row_index == 26:
        return 25
    elif row_index == 27:
        return 25
    elif row_index == 28:
        return 25
    elif row_index == 29:
        return 25
    elif row_index == 30:
        return 25
    elif row_index == 31:
        return 13
    elif row_index == 32:
        return 13
    else:
        return None
