import os
import subprocess
import glob

# Paths
TEST_DIR = "test/schema"
FORMAT_VALIDATOR = "pyvalidator/format_validator_for_test.py"
SCHEMA_VALIDATOR = "pyvalidator/schema_validator_without_ddl.py"

def run_script(script, yaml_file):
    try:
        result = subprocess.run(
            ["python", script, yaml_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def print_header(title):
    print("=" * 70)
    print(title)
    print("=" * 70)

def print_divider():
    print("-" * 70)

def main():
    yaml_files = glob.glob(os.path.join(TEST_DIR, "*.yaml"))
    if not yaml_files:
        print("No YAML test files found.")
        return

    print(f"\nRunning validation for {len(yaml_files)} test cases...\n")

    for yaml_file in sorted(yaml_files):
        print(f"🧪 Testing {os.path.basename(yaml_file)}")

        # Run format validator
        ret_format, out_format, err_format = run_script(FORMAT_VALIDATOR, yaml_file)
        if ret_format != 0:
            print("❌ Format Validation Failed:")
            print("   🔍 Error:")
            # print("   " + (err_format or out_format).replace("\n", "\n   "))
            print(err_format or out_format)
            continue  # Skip schema validation if format fails

        print("✅ Format Validation Passed")

        # Run schema validator
        ret_schema, out_schema, err_schema = run_script(SCHEMA_VALIDATOR, yaml_file)
        if ret_schema != 0:
            print("❌ Schema Validation Failed:")
            print(err_schema or out_schema)
        else:
            print("✅ Schema Validation Passed")

        print_divider()

if __name__ == "__main__":
    main()
