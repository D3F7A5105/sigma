#!/usr/bin/env python3
"""
Checks for logsource or fieldname errors on all rules

Run using the command
# python test_logsource.py
"""

import os
import unittest
import yaml
from colorama import init
from colorama import Fore
import json


class TestRules(unittest.TestCase):

    path_to_rules = "rules"
    
    # Helper functions
    def yield_next_rule_file_path(self, path_to_rules: str) -> str:
        for root, _, files in os.walk(path_to_rules):
            for file in files:
                yield os.path.join(root, file)

    def get_rule_yaml(self, file_path: str) -> dict:
        data = []

        with open(file_path, encoding='utf-8') as f:
            yaml_parts = yaml.safe_load_all(f)
            for part in yaml_parts:
                data.append(part)

        return data
        
    def get_rule_part(self, file_path: str, part_name: str):
        yaml_dicts = self.get_rule_yaml(file_path)
        for yaml_part in yaml_dicts:
            if part_name in yaml_part.keys():
                return yaml_part[part_name]

        return None

    def get_detection_field(self,detection: dict):
        data = []
        
        def get_field_name(selection: dict):
            name = []
            for field in selection:
                if "|" in field:
                    name.append(field.split('|')[0])
                else:
                    name.append(field)
            return name

        for search_identifier in detection:
            if isinstance(detection[search_identifier], dict):
                data += get_field_name(detection[search_identifier])
            if isinstance(detection[search_identifier], list):
               for list_value in detection[search_identifier]:
                    if isinstance(list_value, dict):
                        data += get_field_name(list_value)

        return data        

    def full_logsource(self,logsource: dict) -> dict:
        data = {}
        
        data["product"] = logsource["product"] if "product" in logsource.keys() else None
        data["category"] = logsource["category"] if "category" in logsource.keys() else None
        data["service"] = logsource["service"] if "service" in logsource.keys() else None
        
        return data

    #
    # test functions
    #
    def test_invalid_logsource_attributes(self):
        faulty_rules = []
        valid_logsource = [
            'category',
            'product',
            'service',
            'definition',
        ]
        for file in self.yield_next_rule_file_path(self.path_to_rules):
            logsource = self.get_rule_part(
                file_path=file, part_name="logsource")
            if not logsource:
                print(Fore.RED + "Rule {} has no 'logsource'.".format(file))
                faulty_rules.append(file)
                continue
            valid = True
            for key in logsource:
                if key.lower() not in valid_logsource:
                    print(
                        Fore.RED + "Rule {} has a logsource with an invalid field ({})".format(file, key))
                    valid = False
                elif not isinstance(logsource[key], str):
                    print(
                        Fore.RED + "Rule {} has a logsource with an invalid field type ({})".format(file, key))
                    valid = False
            if not valid:
                faulty_rules.append(file)

        self.assertEqual(faulty_rules, [], Fore.RED +
                         "There are rules with non-conform 'logsource' fields. Please check: https://github.com/SigmaHQ/sigma/wiki/Rule-Creation-Guide#log-source")


    def test_fieldname_case(self):
        files_with_fieldname_issues = []

        def check_category(product,category,fieldname) -> bool:
            valid = True

            if product in fieldname_dict.keys():
                if category in fieldname_dict[product]['category'].keys():
                    if  fieldname in fieldname_dict[product]['category'][category]:
                        pass
                    else:
                        valid = False
            
            return valid

        def check_service(product,service,fieldname) -> bool:
            valid = True

            if product in fieldname_dict.keys():
                if service in fieldname_dict[product]['service'].keys():
                    if  fieldname in fieldname_dict[product]['service'][service]:
                        pass
                    else:
                        valid = False
            
            return valid

        for file in self.yield_next_rule_file_path(self.path_to_rules):
            logsource = self.get_rule_part(file_path=file, part_name="logsource")
            detection = self.get_rule_part(file_path=file, part_name="detection")
            
            if logsource and detection :
                full_logsource = self.full_logsource(logsource)

                #  check the field name
                if full_logsource['product']:
                    if full_logsource['category']:
                        for field in self.get_detection_field(detection):
                            if not check_category(full_logsource['product'],full_logsource['category'],field):
                                print(
                                    Fore.RED + "Rule {} has the invalid field <{}> for category <{}>".format(file, field,full_logsource['category']))
                                files_with_fieldname_issues.append(file)
                    elif full_logsource['service']:
                        for field in self.get_detection_field(detection):
                            if not check_service(full_logsource['product'],full_logsource['service'],field):
                                print(
                                    Fore.RED + "Rule {} has the invalid field <{}> for service <{}>".format(file, field,full_logsource['service']))
                                files_with_fieldname_issues.append(file)                        
                else:
                    if full_logsource['category']:
                        for field in self.get_detection_field(detection):
                            if not check_category("empty",full_logsource['category'],field):
                                print(
                                    Fore.RED + "Rule {} has the invalid field <{}> for category <{}>".format(file, field,full_logsource['category']))
                                files_with_fieldname_issues.append(file)                        

        self.assertEqual(files_with_fieldname_issues, [], Fore.RED +
                         "There are rule files which contains unkown field or with cast error")

def load_fields_json(name:str):
    data = {}

    file_path = os.path.abspath( os.path.dirname( __file__ ) ) +'/'+ name
    with open(file_path, 'r') as file:
        json_dict = json.load(file)
    
    for product in json_dict["legit"]:
        data[product] = json_dict["legit"][product]

    for product in json_dict["addon"]:
        for category in json_dict["addon"][product]["category"]:
            data[product]["category"][category] += json_dict["addon"][product]["category"][category]

    # We use some extracted hash
    # Add commun field
    for product in data:
        for category in data[product]["category"]:
            if "Hashes" in data[product]["category"][category]:
                data[product]["category"][category] += ["md5","sha1","sha256","Imphash"]
            if "Hash" in data[product]["category"][category]: # Sysmon 15 create_stream_hash
                data[product]["category"][category] += ["md5","sha1","sha256","Imphash"]
            if "commun" in data[product].keys():
                data[product]["category"][category] += data[product]["commun"]
        for service in data[product]["service"]:
            if "commun" in data[product].keys():
                data[product]["service"][service] += data[product]["commun"]

    return data

if __name__ == "__main__":
    init(autoreset=True)
    # load field name information
    fieldname_dict = load_fields_json('logsource.json')

    # Run the tests
    unittest.main()
