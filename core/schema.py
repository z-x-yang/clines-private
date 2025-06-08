import pandas as pd
import json
# from model import LLM # This import is no longer needed and model.py is deleted
import sqlite3
from enum import Enum  # Added Enum import
import os
import logging  # Added logging import

# Define Enums for schema names and output types


class SchemaName(Enum):
    I2B2 = "i2b2"
    DEFAULT = "default"


class OutputType(Enum):
    CSV = "csv"
    SQLITE = "sqlite"
    JSON = "json"


# --- Output Formatter Classes ---
class BaseFormatter:
    def __init__(self, output_dir='outputs'):
        self.output_dir = output_dir
        self.logger = logging.getLogger(
            self.__class__.__name__)  # Added logger

    def write(self, data, base_filename):
        raise NotImplementedError("Subclasses must implement this method")


class CsvFormatter(BaseFormatter):
    def write(self, data, base_filename):
        if not data:
            self.logger.warning(
                f"No data provided to CsvFormatter for {base_filename}")
            return
        df_data = pd.DataFrame(data)
        df_data = df_data.replace('(?i)none', pd.NA, regex=True)
        # Ensure base_filename does not already contain .csv
        if base_filename.endswith('.csv'):
            filename = os.path.join(self.output_dir, base_filename)
        else:
            filename = os.path.join(self.output_dir, f"{base_filename}.csv")
        # Added index=False based on typical CSV output needs
        df_data.to_csv(filename, index=False)
        self.logger.info(f"Data written to {filename}")


class SqliteFormatter(BaseFormatter):
    def __init__(self, output_dir='outputs', db_name="sqlite_database.db"):
        super().__init__(output_dir)
        self.db_path = os.path.join(self.output_dir, db_name)
        self.connection = None
        self.cursor = None
        self._connect()

    def _connect(self):
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
        except sqlite3.Error as e:
            self.logger.error(
                f"Error connecting to SQLite database {self.db_path}: {e}", exc_info=True)
            raise  # Re-raise the exception if connection fails

    def write(self, data, table_name):
        if not self.connection:  # Check if connection was successful
            self.logger.error(
                f"Cannot write to SQLite: No database connection to {self.db_path}.")
            return
        if not data:
            self.logger.warning(
                f"No data provided to SqliteFormatter for table {table_name}")
            return
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            self.logger.error(
                "Data for SQLite must be a list of dictionaries.")
            return

        try:
            df = pd.DataFrame(data)
            # Sanitize table_name if necessary, though it should be controlled by schema name
            # table_name = "data" # Or derive from base_filename/schema if needed
            df.to_sql(name=table_name, con=self.connection,
                      if_exists='append', index=False)
            self.connection.commit()
            self.logger.info(
                f"Data written to table {table_name} in {self.db_path}")
        except sqlite3.Error as e:
            self.logger.error(
                f"Error writing to SQLite table {table_name} in {self.db_path}: {e}", exc_info=True)
        except Exception as e:  # Catch other pandas or general errors
            self.logger.error(
                f"Unexpected error writing to SQLite table {table_name}: {e}", exc_info=True)

    def __del__(self):
        if self.connection:
            try:
                self.connection.close()
            except sqlite3.Error as e:
                self.logger.error(
                    f"Error closing SQLite connection to {self.db_path}: {e}", exc_info=True)


class JsonFormatter(BaseFormatter):
    def write(self, data, base_filename):
        if not data:
            self.logger.warning(
                f"No data provided to JsonFormatter for {base_filename}")
            return
        # Ensure base_filename does not already contain .json
        if base_filename.endswith('.json'):
            filename = os.path.join(self.output_dir, base_filename)
        else:
            filename = os.path.join(self.output_dir, f"{base_filename}.json")
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            self.logger.info(f"Data written to {filename}")
        except IOError as e:
            self.logger.error(
                f"Error writing JSON to {filename}: {e}", exc_info=True)
        except TypeError as e:
            self.logger.error(
                f"Error serializing data to JSON for {filename}: {e}", exc_info=True)


# Schema class renamed to SchemaProcessor
class SchemaProcessor():

    def __init__(self, schema_name_str, output_type_str, marker="", output_dir='outputs'):
        self.logger = logging.getLogger(
            self.__class__.__name__)  # Added logger instance
        try:
            self.schema_name = SchemaName(schema_name_str.lower())  # Use Enum
        except ValueError:
            self.logger.error(
                f"Unsupported schema name: {schema_name_str}", exc_info=True)
            raise ValueError(f"Unsupported schema name: {schema_name_str}")

        try:
            self.output_type = OutputType(output_type_str.lower())  # Use Enum
        except ValueError:
            self.logger.error(
                f"Unsupported output type: {output_type_str}", exc_info=True)
            raise ValueError(f"Unsupported output type: {output_type_str}")

        self.marker = marker
        self.output_dir = output_dir
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Instantiate the appropriate formatter
        if self.output_type == OutputType.CSV:
            self.formatter = CsvFormatter(output_dir=self.output_dir)
        elif self.output_type == OutputType.SQLITE:
            # Use schema_name for db_name for now, or a fixed name
            self.formatter = SqliteFormatter(
                output_dir=self.output_dir, db_name=f"{self.schema_name.value}_output.db")
        elif self.output_type == OutputType.JSON:
            self.formatter = JsonFormatter(output_dir=self.output_dir)
        else:
            # This case should ideally not be reached if Enum validation is correct
            raise ValueError(f"Unsupported output type: {self.output_type}")

    def __call__(self, json_data, key_identifier):
        """Processes and writes data based on schema and output type."""
        transformed_data = None
        if self.schema_name == SchemaName.I2B2:
            transformed_data = self._i2b2_transform(json_data, key_identifier)
        elif self.schema_name == SchemaName.DEFAULT:
            transformed_data = self._default_transform(
                json_data, key_identifier)
        else:
            # This case should ideally not be reached if Enum validation is correct
            raise NotImplementedError(
                f"Schema transform not implemented for {self.schema_name}")

        if transformed_data is not None:
            # Determine base_filename or table_name for the formatter
            # For SQLite, the table name might be the schema name or a derivative of key_identifier
            # For file-based formatters, it's usually derived from key_identifier and schema name
            output_name = f"{key_identifier}_{self.schema_name.value}"
            if self.output_type == OutputType.SQLITE:
                # For SQLite, use schema name as table name, or a generic one like "data"
                # Using schema name for table name to distinguish if multiple schemas go to same DB
                self.formatter.write(transformed_data, self.schema_name.value)
            else:
                self.formatter.write(transformed_data, output_name)
        else:
            self.logger.warning(
                f"No data transformed for {key_identifier} with schema {self.schema_name.value}")

    def _default_transform(self, json_data, key_identifier):
        # For default schema, convert dictionary/list fields to JSON strings for CSV compatibility
        processed_data = []

        # Ensure json_data is a list for consistent processing, even if a single dict is passed
        if not isinstance(json_data, list):
            data_to_iterate = [json_data]
        else:
            data_to_iterate = json_data

        for record in data_to_iterate:
            if not isinstance(record, dict):
                self.logger.warning(
                    f"Skipping non-dictionary item in _default_transform for {key_identifier}: {record}")
                continue

            processed_record = {}
            for field_key, field_value in record.items():
                if isinstance(field_value, (dict, list)):
                    try:
                        processed_record[field_key] = json.dumps(field_value)
                    except TypeError as e:
                        self.logger.error(
                            f"Error serializing field '{field_key}' to JSON in _default_transform for {key_identifier}: {e}. Value: {field_value}")
                        # Fallback to string representation
                        processed_record[field_key] = str(field_value)
                else:
                    processed_record[field_key] = field_value
            processed_data.append(processed_record)

        return processed_data

    def _safe_infer_to_string(self, infer_val):
        """Safely convert infer value to string, handling NaN values."""
        if infer_val is None or pd.isna(infer_val):
            return 'false'
        elif isinstance(infer_val, str):
            return infer_val.lower() if infer_val.lower() in ['true', 'false'] else 'false'
        else:
            return str(bool(infer_val)).lower()

    def _i2b2_transform(self, json_data, key_identifier):
        """Transforms input json_data to the i2b2 schema format."""
        output_data = []
        # Ensure json_data is a list for consistent processing
        if not isinstance(json_data, list):
            # This can happen if the upstream LLM call for some tasks returns a single dict
            self.logger.debug(
                f"i2b2_transform received non-list data for {key_identifier} (type: {type(json_data)}), wrapping in list.")
            json_data = [json_data]

        for item in json_data:
            if not isinstance(item, dict):
                self.logger.warning(
                    f"Skipping non-dictionary item in i2b2_transform for {key_identifier}: {item}")
                continue

            value, route, freq = item.get('value', None), item.get(
                'route', None), item.get('freq', None)
            # Extract additional fields for new modifiers
            assertion_status = item.get('assertion_status', None)
            body_location = item.get('body_location', None)
            other = item.get('other', None)
            related = item.get('related', None)
            
            template = {
                # Placeholder, might need actual patient ID from context
                'patient_num': item.get('patient_num', None),
                'birth_date': item.get('birth_date', None),
                'death_date': item.get('death_date', None),
                'sex_cd': item.get('gender', None),
                'race_cd': item.get('race', None),
                'ethnicity_cd': item.get('ethnicity', None),
                'zip_cd': item.get('zip_code', None),
                'encounter_num': key_identifier,  # Use the passed key_identifier
                # Try 'date' if 'begin_date' missing
                'start_date': item.get('begin_date', item.get('date', [None, None])[0]),
                # Try 'date' if 'end_date' missing
                'end_date': item.get('end_date', item.get('date', [None, None])[1]),
                # Use 'TAG' if 'code' is missing (e.g. from NER)
                'concept_cd': item.get('code', item.get('TAG', None)),
                # Use 'CLEAN' if 'mention' is missing
                'name_char': item.get('mention', item.get('CLEAN', None)),
                'observation_blob': item.get('context', None),
                'modifier_cd': '@',  # Default modifier
                'instance_num': 1,  # Base instance
                'valtype_cd': None,
                'tval_char': None,
                'nval_num': None,
                'valueflag_cd': None,
                'units_cd': None,
                'unitflag_cd': 'false',  # Default to 'false', will be updated if needed
                'entity_index': item.get('term_index', None),  # Add term_index field
            }

            # Base record for the entity itself
            current_record = template.copy()
            # If item itself has a value/unit (e.g. for lab results that are entities themselves)
            if item.get('value') is not None and not (value is not None or route is not None or freq is not None):
                try:
                    current_record['nval_num'] = float(item.get('value'))
                    current_record['valtype_cd'] = 'N'
                    # For things like 'greater', 'lower'
                    current_record['tval_char'] = item.get('note', None)
                except (ValueError, TypeError):
                    current_record['tval_char'] = str(item.get('value'))
                    current_record['valtype_cd'] = 'T'
                current_record['units_cd'] = item.get('unit', None)
                # Convert boolean to string 'true'/'false' using safe method
                current_record['unitflag_cd'] = self._safe_infer_to_string(
                    item.get('infer', False))
            else:
                # Ensure unitflag_cd is always set for base records
                current_record['unitflag_cd'] = self._safe_infer_to_string(
                    item.get('infer', False))
            output_data.append(current_record)

            # Modifier records
            # Start instance_num for modifiers from 1 (or 2 if base already had value)
            instance_counter = 1

            if value is not None:
                mod_record = template.copy()
                mod_record['instance_num'] = instance_counter
                instance_counter += 1
                try:
                    mod_record['nval_num'] = float(value)
                    mod_record['valtype_cd'] = 'N'
                    # For things like 'greater', 'lower'
                    mod_record['tval_char'] = item.get('note', None)
                except (ValueError, TypeError):
                    mod_record['tval_char'] = str(value)
                    mod_record['valtype_cd'] = 'T'
                # Or more generic 'VALUE' if not always dose
                mod_record['modifier_cd'] = 'DOSE'
                mod_record['units_cd'] = item.get('unit', None)
                mod_record['unitflag_cd'] = self._safe_infer_to_string(
                    item.get('infer', False))
                output_data.append(mod_record)

            if route is not None:
                mod_record = template.copy()
                mod_record['instance_num'] = instance_counter
                instance_counter += 1
                mod_record['modifier_cd'] = 'ROUTE'
                mod_record['tval_char'] = route
                mod_record['valtype_cd'] = 'T'
                # Ensure unitflag_cd is set
                mod_record['unitflag_cd'] = 'false'
                output_data.append(mod_record)

            if freq is not None:
                mod_record = template.copy()
                mod_record['instance_num'] = instance_counter
                instance_counter += 1
                mod_record['modifier_cd'] = 'FREQ'
                mod_record['tval_char'] = freq
                mod_record['valtype_cd'] = 'T'
                # Ensure unitflag_cd is set
                mod_record['unitflag_cd'] = 'false'
                output_data.append(mod_record)

            # Add new modifier types
            if assertion_status is not None:
                mod_record = template.copy()
                mod_record['instance_num'] = instance_counter
                instance_counter += 1
                mod_record['modifier_cd'] = 'ASSERTION_STATUS'
                mod_record['tval_char'] = str(assertion_status)
                mod_record['valtype_cd'] = 'T'
                mod_record['unitflag_cd'] = 'false'
                output_data.append(mod_record)

            if body_location is not None:
                mod_record = template.copy()
                mod_record['instance_num'] = instance_counter
                instance_counter += 1
                mod_record['modifier_cd'] = 'BODY_LOCATION'
                mod_record['tval_char'] = str(body_location)
                mod_record['valtype_cd'] = 'T'
                mod_record['unitflag_cd'] = 'false'
                output_data.append(mod_record)

            if other is not None:
                mod_record = template.copy()
                mod_record['instance_num'] = instance_counter
                instance_counter += 1
                mod_record['modifier_cd'] = 'OTHER_INFO'
                mod_record['tval_char'] = str(other)
                mod_record['valtype_cd'] = 'T'
                mod_record['unitflag_cd'] = 'false'
                output_data.append(mod_record)

            if related is not None:
                mod_record = template.copy()
                mod_record['instance_num'] = instance_counter
                instance_counter += 1
                mod_record['modifier_cd'] = 'RELATED'
                # Handle related field which may be dict/list or already string
                if isinstance(related, (dict, list)):
                    try:
                        mod_record['tval_char'] = json.dumps(related)
                    except TypeError as e:
                        self.logger.error(
                            f"Error serializing related field to JSON for {key_identifier}: {e}. Value: {related}")
                        mod_record['tval_char'] = str(related)
                else:
                    mod_record['tval_char'] = str(related)
                mod_record['valtype_cd'] = 'T'
                mod_record['unitflag_cd'] = 'false'
                output_data.append(mod_record)

        return output_data
