"""Współrzędne GML, dystans/kierunek, braki danych i raport hydrantów."""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp-servers/mcp-geoportal/src'))
import httpx
import hydrant_client as client
from tools.hydrant_recon import enrich_hydrants
from tools.visualizer import render_html

LAT, LON = 50.255076, 20.173021
NORTH, EAST = client.wgs84_to_puwg1992(LAT, LON)


def gml(points):
    features = ''.join(f'''<hydranty_feature><gml:boundedBy><gml:Box srsName="EPSG:2180">
    <gml:coordinates>{e},{n} {e},{n}</gml:coordinates></gml:Box></gml:boundedBy>
    <id>{i}</id><NAZWA_OBIEKTU>Hydrant</NAZWA_OBIEKTU><DATA>2026-06-12</DATA></hydranty_feature>'''
        for i, e, n in points)
    return f'<msGMLOutput xmlns:gml="http://www.opengis.net/gml">{features}</msGMLOutput>'


class HydrantTests(unittest.TestCase):
    def test_axes_sort_filter_deduplicate_and_unknown_properties(self):
        points, partial = client.parse_hydrants(gml([
            ('far', EAST, NORTH+250), ('near', EAST+30, NORTH),
            ('outside', EAST+1200, NORTH), ('near', EAST+30, NORTH)]), LAT, LON, 500)
        self.assertFalse(partial)
        self.assertEqual([p['id'] for p in points], ['near', 'far'])
        self.assertAlmostEqual(points[0]['distance_m'], 30, delta=0.2)
        self.assertEqual(points[0]['direction'], 'E')
        self.assertEqual(points[0]['estimated_w75_hoses'], 2)
        self.assertEqual(points[0]['type'], 'nieznany')
        self.assertIsNone(points[0]['requires_standpipe_and_key'])
        self.assertEqual(points[0]['source_date'], '2026-06-12')

    def test_reject_nonpoint_box_and_invalid_response(self):
        xml = gml([('x', EAST, NORTH)]).replace(f'{EAST},{NORTH} {EAST},{NORTH}',
                                                         f'{EAST},{NORTH} {EAST+2},{NORTH+2}')
        points, partial = client.parse_hydrants(xml, LAT, LON, 500)
        self.assertEqual(points, [])
        self.assertTrue(partial)
        with self.assertRaises(ValueError):
            client.parse_hydrants('<ServiceExceptionReport/>', LAT, LON, 500)

    def test_query_axes_and_input_validation(self):
        params = client.query_params(LAT, LON, 500)
        self.assertEqual(params['BBOX'], f'{NORTH-500},{EAST-500},{NORTH+500},{EAST+500}')
        for args in [(LAT, LON, 0), (LAT, LON, 3001), (float('nan'), LON, 500)]:
            with self.assertRaises(ValueError):
                client.query_params(*args)

    def run_query(self, body='', status=200):
        async def respond(instance, url, **kwargs):
            return httpx.Response(status, text=body, request=httpx.Request('GET', url))
        with patch.object(httpx.AsyncClient, 'get', respond):
            return asyncio.run(client.get_hydrants_near_point(LAT, LON))

    def test_http_failure_exception_empty_and_limit(self):
        self.assertEqual(self.run_query(status=503)['status'], 'unavailable')
        self.assertEqual(self.run_query('<ServiceExceptionReport/>')['status'], 'unavailable')
        empty = self.run_query(gml([]))
        self.assertEqual(empty['status'], 'no_data')
        self.assertIsNone(empty['nearest_hydrant'])
        with patch.object(client, 'FEATURE_LIMIT', 1):
            self.assertEqual(self.run_query(gml([('x', EAST, NORTH)]))['status'], 'partial')

    def test_report_preserves_intakes_and_renders_provenance_and_map(self):
        recon = self.run_query(gml([('x', EAST+30, NORTH)]))
        data = enrich_hydrants({'weather': {'wind_deg': 0, 'wind_speed_kmh': 10}, 'water_supply': {'open_water_intakes': [{'name': 'Staw'}]}}, recon)
        self.assertEqual(data['water_supply']['open_water_intakes'][0]['name'], 'Staw')
        html = render_html(data)
        for text in ['K-GESUT', '2026-06-12', 'w linii prostej', '<!-- Hydrant x -->']:
            self.assertIn(text, html)
        with self.assertRaises(ValueError):
            enrich_hydrants({'incident_info': {'lat': 52}}, recon)
