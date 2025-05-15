# import os
# import subprocess
# import glob

# # Paths
# TEST_DIR = "test/semantics"
# SEMANTIC_VALIDATOR = "pyvalidator/semantic_validator_for_test.py"

# def run_script(script, yaml_file):
#     try:
#         result = subprocess.run(
#             ["python", script, yaml_file],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )
#         return result.returncode, result.stdout.strip(), result.stderr.strip()
#     except Exception as e:
#         return -1, "", str(e)

# def print_header(title):
#     print("=" * 70)
#     print(title)
#     print("=" * 70)

# def print_divider():
#     print("-" * 70)

# def main():
#     yaml_files = glob.glob(os.path.join(TEST_DIR, "*.yaml"))
#     if not yaml_files:
#         print("No YAML test files found in 'test/semantics'")
#         return

#     print_header(f"Running Semantics Validation for {len(yaml_files)} Test Cases")

#     for yaml_file in sorted(yaml_files):
#         print(f"🧪 Testing {os.path.basename(yaml_file)}")

#         ret_sem, out_sem, err_sem = run_script(SEMANTIC_VALIDATOR, yaml_file)
#         if ret_sem != 0:
#             print("❌ Semantic Validation Failed:")
#             print(err_sem or out_sem)
#         else:
#             print("✅ Semantic Validation Passed")
#             print(out_sem)

#         print_divider()

# if __name__ == "__main__":
#     main()

































































































# import os
# import subprocess
# import glob
# import yaml
# from pathlib import Path
# from pydantic import ValidationError

# from pyvalidator.semantic_validator_for_test import SemanticsModel
# from pyvalidator.semantic_validator_for_test import load_schema
# from pyvalidator.semantic_validator_for_test import replace_all_in_source
# from pyvalidator.semantic_validator_for_test import get_custom_error_type

# # Paths
# TEST_DIR = "test/semantics"
# SEMANTIC_VALIDATOR = "pyvalidator/semantic_validator_for_test.py"

# def run_script(script, yaml_file):
#     try:
#         result = subprocess.run(
#             ["python", script, yaml_file],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )
#         return result.returncode, result.stdout.strip(), result.stderr.strip()
#     except Exception as e:
#         return -1, "", str(e)

# def print_header(title):
#     print("=" * 70)
#     print(title)
#     print("=" * 70)

# def print_divider():
#     print("-" * 70)

# def main():
#     yaml_files = glob.glob(os.path.join(TEST_DIR, "*.yaml"))
#     if not yaml_files:
#         print("No YAML test files found.")
#         return

#     print(f"\nRunning validation for {len(yaml_files)} semantic test cases...\n")

#     for yaml_file in sorted(yaml_files):
#         print(f"🧪 Testing {os.path.basename(yaml_file)}")

#         # Run semantic validator
#         ret_semantic, out_semantic, err_semantic = run_script(SEMANTIC_VALIDATOR, yaml_file)
#         if ret_semantic != 0:
#             print("❌ Semantic Validation Failed:")
#             print(err_semantic or out_semantic)
#         else:
#             print("✅ Semantic Validation Passed")

#         print_divider()

# if __name__ == "__main__":
#     import sys

#     schema_path = "assets/schema/game.yml"

#     semantics_validator = SemanticsModel
#     all_semantic_files = sorted(Path("test/semantics").glob("*.yaml"), key=lambda f: int("".join(filter(str.isdigit, f.name))))
#     schema_lookup = {}
#     column_keys = []  # Initialize column_keys here as an empty list

#     try:
#         print("📦 Fetching schema...")
#         schema_cols = load_schema(schema_path)
#         schema_lookup = {
#             subject_area.lower(): {
#                 "columns": columns
#             } for subject_area, columns in schema_cols.items()
#         }
#         # Ensure column_keys is populated from the schema
#         column_keys = list(schema_lookup.values())[0]["columns"]  # Initialize column_keys from schema_lookup
#         print('🧩 Column Keys:', column_keys)
#     except Exception as e:
#         print(f"⚠️ Error loading schema: {e}")
#         sys.exit(1)

#     for semantic_file in all_semantic_files:
#         try:
#             print(f"\n📄 Processing file: {semantic_file.name}")
#             with open(semantic_file, 'r') as f:
#                 file_content = f.read()
#                 if not file_content.strip():
#                     print(f"❌ EmptyFileError: {semantic_file.name} is empty or only contains whitespace")
#                     continue
#                 try:
#                     data = yaml.safe_load(file_content)
#                 except yaml.YAMLError as e:
#                     print(f"🔴 InvalidFormatError: {semantic_file.name} - {e}")
#                     continue

#             try:
#                 replace_all_in_source(data, schema_lookup)
#             except Exception as e:
#                 print(f"⚠️ Error processing <all>: {e}")
#                 continue

#             try:
#                 print(f"🧪 Validating {semantic_file.name}")
#                 validated = semantics_validator.model_validate(data)
#                 print(f"✅ Passed: {semantic_file.name}")
#             except ValidationError as e:
#                 print(f"❌ Validation Failed: {semantic_file.name}")
#                 for err in e.errors():
#                     custom_error = get_custom_error_type(err)
#                     print(f"🔴 {custom_error}: {'.'.join(str(i) for i in err['loc'])} - {err['msg']}")

#         except Exception as e:
#             print(f"⚠️ Error processing file {semantic_file.name}: {e}")
