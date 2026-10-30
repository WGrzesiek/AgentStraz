import copy
import unittest
from tools.report_panels import combined_plan
from tools.visualizer import render_html

class TestReportPanels(unittest.TestCase):
    def test_water_panel_separates_sources_and_computes_scenario(self):
        data = {'building': {'footprint_area_m2': 127.38, 'height_m': 6.91,
                             'source_url': 'https://example.org/model.zip'},
                'suppression': {'fire_area_m2': 127.38,
                                'area_assumption': 'Scenariusz: jeden rzut'}}
        html = render_html(data)
        panel = html.split('Kubatura i zapotrzebowanie wody — szacunek',1)[1].split('</section>',1)[0]
        self.assertIn('611.4–764.3 l/min',panel)
        self.assertIn('12,23–15,29 m³',panel)
        self.assertIn('Scenariusz: jeden rzut',panel)
        self.assertNotIn('https://',panel)
        self.assertIn('https://example.org/model.zip',html)

    def test_overlay_projects_known_point_and_omits_unknown_location(self):
        from pathlib import Path
        import importlib.util
        spec = importlib.util.spec_from_file_location('test_coords', Path('mcp-servers/mcp-geoportal/src/coords.py'))
        coords = importlib.util.module_from_spec(spec); spec.loader.exec_module(coords)
        north,east = coords.wgs84_to_puwg1992(50.255076,20.173021)
        data = {'building': {'site_plan': {'crs':'EPSG:2180',
            'origin_easting':east,'origin_northing':north,'radius_m':80,
            'selected_id':None,'features':[{'id':'test','polygons':[[[
                [east-5,north-5],[east+5,north-5],[east+5,north+5],
                [east-5,north+5],[east-5,north-5]]]]}]}},
            'water_supply':{'open_water_intakes':[
                {'lat':50.2546337,'lon':20.1721423,'name':'<script>bad</script>'},
                {'distance_m':50,'bearing_deg':90,'name':'Znany azymut'},
                {'distance_m':200,'bearing_deg':90,'name':'Poza kadrem'},
                {'distance_m':501,'bearing_deg':90,'name':'Poza 500 m'},
                {'distance_m':50,'name':'Nieznana pozycja'}]}}
        original = copy.deepcopy(data)
        html = combined_plan(data)
        self.assertIn('data-water-id="W1"',html)
        self.assertIn('data-water-id="W2"',html)
        self.assertIn('data-water-id="W3"',html)
        import re
        outside_line = re.search(r'<line data-water-id="W3"[^>]+>', html).group()
        self.assertNotIn('marker-end', outside_line)
        x = float(re.search(r'x2="([^"]+)"', outside_line).group(1))
        y = float(re.search(r'y2="([^"]+)"', outside_line).group(1))
        self.assertAlmostEqual(max(abs(x-290), abs(y-290)), 240, places=2)
        self.assertRegex(html, r'~20[01] m · E · poza kadrem')
        inside_line = re.search(r'<line data-water-id="W2"[^>]+>', html).group()
        self.assertIn('marker-end', inside_line)
        self.assertIn('poza kadrem szkicu',html)
        self.assertNotIn('Poza 500 m',html)
        self.assertNotIn('Nieznana pozycja',html)
        self.assertIn('Pozycja orientacyjna z podanego azymutu',html)
        self.assertIn('Zasięg: ±80 m',html)
        self.assertIn('max-width:600px',html)
        # Daleki punkt nie zmienia skali ani współrzędnych obrysów.
        import re
        from tools.building_sketch import _render_plan
        pattern = r'<path data-building-id="[^"]+" d="[^"]+"'
        self.assertEqual(re.findall(pattern, html),
                         re.findall(pattern, _render_plan(data['building']['site_plan'])))
        self.assertIn('~80 m · SW',html)
        self.assertIn('combined-plan-clip',html)
        self.assertNotIn('<script>bad',html)
        self.assertIn('Nie wybrano budynku',html)
        self.assertEqual(data,original)

    def test_missing_geometry_has_no_invented_plan(self):
        html = combined_plan({})
        self.assertIn('Brak geometrii',html)
        self.assertNotIn('<svg',html)
