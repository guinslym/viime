from io import BytesIO
import math

from flask import url_for
import pandas
from pandas.testing import assert_frame_equal
import pytest

from metabulo import normalization
from metabulo import scaling
from metabulo import transformation
from metabulo.models import CSVFile


@pytest.fixture
def table(app):
    with app.app_context():
        yield pandas.read_csv(BytesIO(b"""
id,col1,col2
row1,0.5,2.0
row2,1.5,0.0
"""), index_col=0)


def test_normalize_minmax(table):
    correct = table.copy()
    correct[:] = [[0.0, 1.0], [1.0, 0.0]]
    t = normalization.normalize('minmax', table)
    assert_frame_equal(t, correct)


def test_normalize_none(table):
    correct = table.copy()
    t = normalization.normalize(None, table)
    assert_frame_equal(t, correct)


def test_normalize_api(client, csv_file):
    resp = client.put(
        url_for('csv.set_normalization_method', csv_id=csv_file.id), json={'method': 'minmax'}
    )
    assert resp.status_code == 200
    assert resp.json == 'minmax'
    assert abs(CSVFile.query.get(csv_file.id).measurement_table.iloc[0, 0]) < 1e-8

    resp = client.put(
        url_for('csv.set_normalization_method', csv_id=csv_file.id), json={'method': None}
    )
    assert resp.status_code == 200
    assert resp.json is None
    assert CSVFile.query.get(csv_file.id).measurement_table.iloc[0, 0] == 0.5


def test_scale_none(table):
    correct = table.copy()
    t = scaling.scale(None, table)
    assert_frame_equal(t, correct)


def test_scale_auto(table):
    t = scaling.scale('auto', table)
    assert abs(t.iloc[0, 0] + math.sqrt(0.5)) < 1e-8


def test_scale_api(client, csv_file):
    resp = client.put(
        url_for('csv.set_scaling_method', csv_id=csv_file.id), json={'method': 'auto'}
    )
    assert resp.status_code == 200
    assert resp.json == 'auto'
    assert abs(CSVFile.query.get(csv_file.id).measurement_table.iloc[0, 0] + math.sqrt(0.5)) < 1e-8

    resp = client.put(
        url_for('csv.set_scaling_method', csv_id=csv_file.id), json={'method': None}
    )
    assert resp.status_code == 200
    assert resp.json is None
    assert CSVFile.query.get(csv_file.id).measurement_table.iloc[0, 0] == 0.5


def test_transform_none(table):
    correct = table.copy()
    t = transformation.transform(None, table)
    assert_frame_equal(t, correct)


def test_transform_log10(table):
    t = transformation.transform('log10', table)
    assert abs(t.iloc[0, 0] - math.log10(0.5)) < 1e-8


def test_transform_api(client, csv_file):
    csv_file = CSVFile.query.get(csv_file.id)
    resp = client.put(
        url_for('csv.set_transformation_method', csv_id=csv_file.id), json={'method': 'squareroot'}
    )
    assert resp.status_code == 200
    assert resp.json == 'squareroot'
    assert CSVFile.query.get(csv_file.id).measurement_table.iloc[0, 0] == math.sqrt(0.5)

    resp = client.put(
        url_for('csv.set_transformation_method', csv_id=csv_file.id), json={'method': None}
    )
    assert resp.status_code == 200
    assert resp.json is None
    assert CSVFile.query.get(csv_file.id).measurement_table.iloc[0, 0] == 0.5
