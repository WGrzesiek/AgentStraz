import copy
import tempfile
import unittest
from pathlib import Path

from skills.demo_runner import run_tactical_demo
from tools.visualizer import (
    DEFAULT_DEMO_DATA, generate_report_file, generate_tactical_svg,
    parse_text_recon, render_html,
)


class TestReportIntegration(unittest.TestCase):
    def test_partial_text_never_uses_demo_facts(self):
        data = parse_text_recon('Adres: Testowa 7')
        self.assertEqual(data['incident_info'], {'address': 'Testowa 7', 'city': 'Testowa 7'})
        self.assertEqual(data['weather'], {})
        self.assertEqual(data['water_supply']['hydrants'], [])
        html = render_html(data)
        for fictional in ['Sosnowa', 'TRAFO 130m', 'ZASUWA GAZ', 'GCBA PRZEJEZDNE', '14:22']:
            self.assertNotIn(fictional, html)
        self.assertIn('PRZEJEZDNOŚĆ NIEPOTWIERDZONA', html)

    def test_markdown_template_parses_supplied_data(self):
        data = parse_text_recon(Path('examples/sample_recon.md').read_text())
        self.assertEqual(data['weather']['wind_deg'], 315)
        self.assertEqual(len(data['water_supply']['hydrants']), 2)
        self.assertTrue(data['water_supply']['hydrants'][1]['requires_standpipe_and_key'])
        self.assertEqual(data['water_supply']['open_water_intakes'][0]['name'], 'Rzeka Mienia')
        self.assertIsNone(data['water_supply']['hydrants'][0]['bearing_deg'])
        self.assertIn('utwardzony', data['water_supply']['open_water_intakes'][0]['access_road'])

    def test_html_escapes_external_text_without_mutating_input(self):
        data = copy.deepcopy(DEFAULT_DEMO_DATA)
        data['incident_info']['address'] = '<img src=x onerror=alert(1)>'
        data['radio_brief'] = '</textarea><script>alert(1)</script>'
        original = copy.deepcopy(data)
        html = render_html(data)
        self.assertNotIn('<img src=x', html)
        self.assertNotIn('</textarea><script>alert(1)', html)
        self.assertIn('&lt;img', html)
        self.assertEqual(data, original)

    def test_map_omits_unknown_bearings_and_outside_radius(self):
        data = copy.deepcopy(DEFAULT_DEMO_DATA)
        data['water_supply']['hydrants'][0]['bearing_deg'] = None
        data['water_supply']['hydrants'][1]['distance_m'] = 900
        svg = generate_tactical_svg(data)
        self.assertNotIn('<!-- Hydrant H1 -->', svg)
        self.assertNotIn('<!-- Hydrant H2 -->', svg)
        self.assertNotIn('TRAFO 130m', svg)

    def test_demo_writes_common_markdown_json_html(self):
        import contextlib
        import io
        import json
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            run_tactical_demo(tmp)
            data = json.loads((Path(tmp) / 'karta_skills.json').read_text())
            html = (Path(tmp) / 'karta_skills.html').read_text()
            md = (Path(tmp) / 'karta_skills.md').read_text()
            self.assertEqual(data['water_supply']['hydrants'][0]['estimated_w75_hoses'], 6)
            self.assertEqual(data['weather']['hazard_cone_span_deg'], 90)
            self.assertIn('DEMO — DANE FIKCYJNE', html)
            self.assertIn('6 szt.', md)
            self.assertIn('6 odcinków W-75', html)
            self.assertIn('Stojak', md)
            self.assertIn('WYMAGANY STOJAK', html)
            self.assertEqual(data['building_water']['volume_m3'], 720)
            self.assertEqual(data['building_water']['flow_l_min']['max'], 600)
            self.assertIn('720.0 m³', md)
            self.assertIn('720.0 m³', html)
            self.assertIn('9600.0–12000.0 l', md)
            self.assertIn('9600.0–12000.0 l', html)
            generate_report_file(str(Path(tmp) / 'karta_skills.json'), str(Path(tmp) / 'again.html'))
            self.assertEqual((Path(tmp) / 'again.html').read_text(), html)


if __name__ == '__main__':
    unittest.main()
