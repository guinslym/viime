from io import BytesIO
import os

from flask import Blueprint, current_app, jsonify, request, send_file
from sklearn import preprocessing

from metabulo.models import CreateCSVFileSchema, CSVFile, CSVFileSchema, db


csv_file_schema = CSVFileSchema()
create_csv_file_schema = CreateCSVFileSchema()

csv_bp = Blueprint('csv', __name__)


@csv_bp.route('/csv/upload', methods=['POST'])
def upload_csv_file():
    if 'file' not in request.files:
        return jsonify('No file provided in request'), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify('No file selected'), 400

    csv_file_args = create_csv_file_schema.load({
        'name': file.filename
    })
    file.save(csv_file_args['uri'])

    try:
        csv_file = csv_file_schema.load(csv_file_args)
        db.session.add(csv_file)
        db.session.commit()

        return jsonify(csv_file_schema.dump(csv_file)), 201
    except Exception:
        os.unlink(csv_file_args['uri'])
        db.session.rollback()
        raise


@csv_bp.route('/csv', methods=['POST'])
def create_csv_file():
    csv_file_args = create_csv_file_schema.load(request.json)
    with open(csv_file_args['uri'], 'w') as f:
        f.write(csv_file_args['table'])

    try:
        csv_file = csv_file_schema.load(csv_file_args)
        db.session.add(csv_file)
        db.session.commit()

        return jsonify(csv_file_schema.dump(csv_file)), 201
    except Exception:
        os.unlink(csv_file_args['uri'])
        db.session.rollback()
        raise


@csv_bp.route('/csv/<uuid:csv_id>', methods=['GET'])
def get_csv_file(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    return jsonify(csv_file_schema.dump(csv_file))


@csv_bp.route('/csv/<uuid:csv_id>/download', methods=['GET'])
def download_csv_file(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    fp = BytesIO(csv_file.table.to_csv().encode())
    return send_file(fp, mimetype='text/csv', as_attachment=True, attachment_filename=csv_file.name)


@csv_bp.route('/csv/<uuid:csv_id>', methods=['DELETE'])
def delete_csv_file(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    csv_file.delete()
    db.session.commit()

    try:
        os.unlink(csv_file.uri)
    except Exception as e:
        current_app.logger.exception(e)

    return '', 204


@csv_bp.route('/csv/<uuid:csv_id>/normalize/<column>', methods=['PUT'])
def normalize_row(csv_id, column):
    csv_file = CSVFile.query.get_or_404(csv_id)
    table = csv_file.table
    column_data = table[[column]].values.astype(float)
    min_max_scalar = preprocessing.MinMaxScaler()
    table[[column]] = min_max_scalar.fit_transform(column_data)

    return csv_file.save_table()


@csv_bp.route('/csv/uuid:csv_id>/fill/<column>', methods=['PUT'])
def fill_missing_values(csv_id, column):
    value = request.json.get('value')
    csv_file = CSVFile.query.get_or_404(csv_id)
    table = csv_file.table
    if value is None:
        value = table[column].mean()
    table[column] = table[column].fillna(value)

    return csv_file.save_table()
