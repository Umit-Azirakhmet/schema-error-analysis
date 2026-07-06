# Characteristic Distributions

Active columns only (from `data/active_characteristics.json`).

## ARQA (535 rows)

| Column | Distribution |
|--------|--------------|
| `char_has_table_cells` | 531/535 (99.3%) = 1 |
| `char_has_text_spans` | 532/535 (99.4%) = 1 |
| `table_cell_total_refs_count` | min=0, p25=2.0, med=2.0, mean=2.3, p75=2.0, max=9, nonzero=533/535 (99.6%) |
| `claim_count` | min=0, p25=2.0, med=2.0, mean=2.4, p75=3.0, max=6, nonzero=533/535 (99.6%) |
| `max_evidence_items_per_claim` | min=0, p25=2.0, med=2.0, mean=1.9, p75=2.0, max=6, nonzero=533/535 (99.6%) |
| `gold_json_length` | min=485, p25=1005.0, med=1163.0, mean=1208.4, p75=1362.0, max=2897, nonzero=535/535 (100.0%) |
| `total_object_count` | min=4, p25=8.0, med=8.0, mean=9.3, p75=11.0, max=20, nonzero=535/535 (100.0%) |
| `total_array_count` | min=2, p25=3.0, med=3.0, mean=3.4, p75=4.0, max=7, nonzero=535/535 (100.0%) |
| `max_array_length` | min=1, p25=2.0, med=2.0, mean=2.4, p75=3.0, max=6, nonzero=535/535 (100.0%) |
| `total_key_count` | min=10, p25=22.0, med=22.0, mean=25.7, p75=30.0, max=58, nonzero=535/535 (100.0%) |
| `unique_key_count` | min=10, p25=15.0, med=15.0, mean=15.0, p75=15.0, max=15, nonzero=535/535 (100.0%) |
| `max_key_length` | min=10, p25=11.0, med=11.0, mean=11.0, p75=11.0, max=12, nonzero=535/535 (100.0%) |
| `long_text_value_count` | min=3, p25=4.0, med=5.0, mean=5.1, p75=6.0, max=13, nonzero=535/535 (100.0%) |
| `numeric_value_count` | min=2, p25=5.0, med=6.0, mean=6.2, p75=7.5, max=14, nonzero=535/535 (100.0%) |
| `alphanumeric_value_count` | min=2, p25=6.0, med=7.0, mean=7.8, p75=9.0, max=21, nonzero=535/535 (100.0%) |
| `max_value_length` | min=108, p25=178.0, med=208.0, mean=223.4, p75=251.5, max=712, nonzero=535/535 (100.0%) |
| `average_value_length` | min=21, p25=34.3, med=41.8, mean=42.8, p75=49.0, max=120, nonzero=535/535 (100.0%) |
| `value_types` | number, string (534, 99.8%); string (1, 0.2%) |

## DeepJSONEval (263 rows)

| Column | Distribution |
|--------|--------------|
| `array_of_objects` | 232/263 (88.2%) = 1 |
| `array_of_primitives` | 135/263 (51.3%) = 1 |
| `has_enum` | 138/263 (52.5%) = 1 |
| `property_count` | min=5, p25=11.0, med=12.0, mean=12.3, p75=14.0, max=18, nonzero=263/263 (100.0%) |
| `gold_json_length` | min=125, p25=379.5, med=473.0, mean=490.0, p75=588.0, max=1023, nonzero=263/263 (100.0%) |
| `nesting_depth` | min=3, p25=4.0, med=5.0, mean=4.9, p75=6.0, max=7, nonzero=263/263 (100.0%) |
| `total_object_count` | min=4, p25=9.0, med=10.0, mean=10.3, p75=12.0, max=21, nonzero=263/263 (100.0%) |
| `max_array_nesting_depth` | min=0, p25=1.0, med=1.0, mean=1.3, p75=2.0, max=2, nonzero=255/263 (97.0%) |
| `total_array_count` | min=0, p25=1.0, med=2.0, mean=2.7, p75=4.0, max=9, nonzero=255/263 (97.0%) |
| `max_array_length` | min=0, p25=3.0, med=3.0, mean=3.1, p75=3.0, max=9, nonzero=255/263 (97.0%) |
| `total_key_count` | min=6, p25=14.0, med=18.0, mean=17.2, p75=20.0, max=31, nonzero=263/263 (100.0%) |
| `unique_key_count` | min=5, p25=10.0, med=12.0, mean=11.9, p75=14.0, max=17, nonzero=263/263 (100.0%) |
| `max_key_length` | min=8, p25=14.0, med=15.0, mean=15.6, p75=18.0, max=19, nonzero=263/263 (100.0%) |
| `long_text_value_count` | min=0, p25=0.0, med=0.0, mean=1.1, p75=2.0, max=8, nonzero=129/263 (49.0%) |
| `numeric_value_count` | min=0, p25=1.0, med=3.0, mean=3.1, p75=5.0, max=13, nonzero=226/263 (85.9%) |
| `alphanumeric_value_count` | min=0, p25=0.0, med=1.0, mean=1.1, p75=2.0, max=10, nonzero=161/263 (61.2%) |
| `max_value_length` | min=5, p25=18.5, med=25.0, mean=28.4, p75=34.0, max=80, nonzero=263/263 (100.0%) |
| `average_value_length` | min=3, p25=8.2, med=10.5, mean=12.4, p75=15.7, max=42, nonzero=263/263 (100.0%) |
| `value_types` | number, string (120, 45.6%); boolean, number, string (97, 36.9%); boolean, string (25, 9.5%); string (19, 7.2%); boolean, number (2, 0.8%) |

## SchemaToJSON (500 rows)

| Column | Distribution |
|--------|--------------|
| `escaping_count` | min=8, p25=120.0, med=240.0, mean=388.5, p75=472.0, max=5172, nonzero=500/500 (100.0%) |
| `numeric_string_count` | min=1, p25=14.0, med=25.0, mean=38.0, p75=48.0, max=527, nonzero=500/500 (100.0%) |
| `cell_record_count` | min=1, p25=14.0, med=25.0, mean=36.6, p75=45.0, max=288, nonzero=500/500 (100.0%) |
| `duplicate_record_count` | min=0, p25=0.0, med=2.0, mean=2.3, p75=3.0, max=40, nonzero=289/500 (57.8%) |
| `table_cell_ref` | 110/500 (22.0%) = 1 |
| `long_text` | 210/500 (42.0%) = 1 |
| `gold_json_length` | min=87, p25=881.0, med=1731.0, mean=2810.6, p75=3373.5, max=36918, nonzero=500/500 (100.0%) |
| `total_object_count` | min=2, p25=15.0, med=26.0, mean=37.6, p75=46.0, max=289, nonzero=500/500 (100.0%) |
| `total_array_count` | min=3, p25=16.0, med=27.0, mean=38.6, p75=47.0, max=290, nonzero=500/500 (100.0%) |
| `max_array_length` | min=3, p25=14.0, med=25.0, mean=36.6, p75=45.0, max=288, nonzero=500/500 (100.0%) |
| `total_key_count` | min=4, p25=32.0, med=62.0, mean=99.1, p75=120.0, max=1295, nonzero=500/500 (100.0%) |
| `unique_key_count` | min=4, p25=4.0, med=4.0, mean=4.8, p75=7.0, max=7, nonzero=500/500 (100.0%) |
| `long_text_value_count` | min=0, p25=0.0, med=0.0, mean=0.1, p75=0.0, max=18, nonzero=5/500 (1.0%) |
| `numeric_value_count` | min=4, p25=56.0, med=100.0, mean=147.7, p75=184.0, max=1391, nonzero=500/500 (100.0%) |
| `alphanumeric_value_count` | min=0, p25=0.0, med=0.0, mean=9.5, p75=4.2, max=225, nonzero=127/500 (25.4%) |
| `max_value_length` | min=5, p25=5.0, med=5.0, mean=9.4, p75=21.0, max=31, nonzero=500/500 (100.0%) |
| `average_value_length` | min=1, p25=2.3, med=2.4, mean=2.8, p75=3.1, max=7, nonzero=500/500 (100.0%) |
