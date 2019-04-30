from io import BytesIO
import json

from flask import Blueprint, current_app, jsonify, request, Response, send_file
from marshmallow import fields, validate, ValidationError
import pandas
from webargs.flaskparser import use_kwargs

from metabulo import opencpu
from metabulo.cache import csv_file_cache
from metabulo.imputation import IMPUTE_MCAR_METHODS, IMPUTE_MNAR_METHODS
from metabulo.models import AXIS_NAME_TYPES, CSVFile, CSVFileSchema, db, \
    ModifyLabelListSchema, \
    TABLE_COLUMN_TYPES, TABLE_ROW_TYPES, \
    TableColumn, TableColumnSchema, TableRow, \
    TableRowSchema
from metabulo.normalization import NORMALIZATION_METHODS
from metabulo.opencpu import OpenCPUException
from metabulo.plot import pca
from metabulo.scaling import SCALING_METHODS
from metabulo.table_validation import get_fatal_index_errors, ValidationSchema
from metabulo.transformation import TRANSFORMATION_METHODS

csv_file_schema = CSVFileSchema()
modify_label_list_schema = ModifyLabelListSchema()
table_column_schema = TableColumnSchema(exclude=['csv_file'])
table_row_schema = TableRowSchema(exclude=['csv_file'])
validation_schema = ValidationSchema()

csv_bp = Blueprint('csv', __name__)


@csv_file_cache
def _serialize_csv_file(csv_file):
    csv_file_schema = CSVFileSchema()
    return csv_file_schema.dump(csv_file)


@csv_bp.route('/csv/upload', methods=['POST'])
def upload_csv_file():
    if 'file' not in request.files:
        return jsonify('No file provided in request'), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify('No file selected'), 400

    csv_file = None
    meta_string = request.form.get('meta', '{}')
    try:
        meta = json.loads(meta_string)
    except Exception:
        raise ValidationError(
            'Expected a json encoded string for metadata', field_name='meta', data=meta_string)

    try:
        csv_file = csv_file_schema.load({
            'name': file.filename,
            'table': file.read().decode(),
            'meta': meta
        })

        db.session.add(csv_file)
        db.session.commit()

        return jsonify(_serialize_csv_file(csv_file)), 201
    except Exception:
        if csv_file and csv_file.uri.is_file():
            csv_file.uri.unlink()
        db.session.rollback()
        raise


@csv_bp.route('/csv', methods=['POST'])
def create_csv_file():
    csv_file = None
    try:
        csv_file = csv_file_schema.load(request.json)
        db.session.add(csv_file)
        db.session.commit()

        return jsonify(_serialize_csv_file(csv_file)), 201
    except Exception:
        if csv_file and csv_file.uri.is_file():
            csv_file.uri.unlink()
        db.session.rollback()
        raise


@csv_bp.route('/csv/<uuid:csv_id>', methods=['GET'])
def get_csv_file(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    return jsonify(_serialize_csv_file(csv_file))


@csv_bp.route('/csv/<uuid:csv_id>/validation', methods=['GET'])
def get_csv_file_validation(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    return jsonify(validation_schema.dump(csv_file.table_validation, many=True))


@csv_bp.route('/csv/<uuid:csv_id>/metadata', methods=['PUT'])
def set_csv_file_metadata(csv_id):
    try:
        csv_file = CSVFile.query.get_or_404(csv_id)
        csv_file.meta = request.json
        db.session.add(csv_file)
        db.session.commit()
        return jsonify(csv_file_schema.dump(csv_file))
    except Exception:
        db.session.rollback()
        raise


@csv_bp.route('/csv/<uuid:csv_id>/download', methods=['GET'])
def download_csv_file(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    fp = BytesIO(csv_file.table.to_csv(header=False, index=False).encode())
    return send_file(fp, mimetype='text/csv', as_attachment=True, attachment_filename=csv_file.name)


@csv_bp.route('/csv/<uuid:csv_id>', methods=['DELETE'])
def delete_csv_file(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)

    try:
        TableRow.query.filter_by(csv_file_id=csv_id).delete()
        TableColumn.query.filter_by(csv_file_id=csv_id).delete()
        db.session.delete(csv_file)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    try:
        csv_file.uri.unlink()
    except Exception as e:
        current_app.logger.exception(e)

    return '', 204

# Missing data imputation options
@csv_bp.route('/csv/<uuid:csv_id>/imputation', methods=['GET'])
def get_imputation_options(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    return jsonify({
        'imputation_mcar': csv_file.imputation_mcar,
        'imputation_mnar': csv_file.imputation_mnar
    })


@csv_bp.route('/csv/<uuid:csv_id>/imputation', methods=['PUT'])
@use_kwargs({
    'mcar': fields.Str(validate=validate.OneOf(IMPUTE_MCAR_METHODS)),
    'mnar': fields.Str(validate=validate.OneOf(IMPUTE_MNAR_METHODS))
})
def set_imputation_options(csv_id, **kwargs):
    csv_file = CSVFile.query.get_or_404(csv_id)

    try:
        if 'mcar' in kwargs:
            csv_file.imputation_mcar = kwargs['mcar']
        if 'mnar' in kwargs:
            csv_file.imputation_mnar = kwargs['mnar']
        db.session.add(csv_file)
        db.session.commit()
        return jsonify({
            'imputation_mcar': csv_file.imputation_mcar,
            'imputation_mnar': csv_file.imputation_mnar
        })
    except Exception:
        db.session.rollback()
        raise


# Ingest transforms
@csv_bp.route('/csv/<uuid:csv_id>/normalization', methods=['PUT'])
def set_normalization_method(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    args = request.json
    method = args['method']
    if method is not None and method not in NORMALIZATION_METHODS:
        raise ValidationError('Invalid normalization method', data=method)
    try:
        csv_file.normalization = method
        db.session.add(csv_file)
        db.session.commit()
        return jsonify(method)
    except Exception:
        db.session.rollback()
        raise


@csv_bp.route('/csv/<uuid:csv_id>/transformation', methods=['PUT'])
def set_transformation_method(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    args = request.json
    method = args['method']
    if method is not None and method not in TRANSFORMATION_METHODS:
        raise ValidationError('Invalid transformation method', data=method)
    try:
        csv_file.transformation = method
        db.session.add(csv_file)
        db.session.commit()
        return jsonify(method)
    except Exception:
        db.session.rollback()
        raise


@csv_bp.route('/csv/<uuid:csv_id>/scaling', methods=['PUT'])
def set_scaling_method(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    args = request.json
    method = args['method']
    if method is not None and method not in SCALING_METHODS:
        raise ValidationError('Invalid scaling method', data=method)
    try:
        csv_file.scaling = method
        db.session.add(csv_file)
        db.session.commit()
        return jsonify(method)
    except Exception:
        db.session.rollback()
        raise


# Row/Column API
@csv_bp.route('/csv/<uuid:csv_id>/column', methods=['GET'])
def list_columns(csv_id):
    CSVFile.query.get_or_404(csv_id)  # ensure the file exists
    return jsonify(table_column_schema.dump(
        TableColumn.query.filter_by(csv_file_id=csv_id),
        many=True
    ))


@csv_bp.route('/csv/<uuid:csv_id>/column/<int:column_index>', methods=['GET'])
def get_column(csv_id, column_index):
    return jsonify(table_column_schema.dump(
        TableColumn.query.get_or_404((csv_id, column_index))
    ))


@csv_bp.route('/csv/<uuid:csv_id>/batch/label', methods=['PUT'])
def batch_modify_label(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    args = modify_label_list_schema.load(request.json or {})

    for change in args['changes']:
        index = change['index']
        label = change['label']
        context = change['context']

        if context == AXIS_NAME_TYPES.ROW:
            row = TableRow.query.get_or_404((csv_id, index))
            if label == TABLE_ROW_TYPES.INDEX:
                csv_file.header_row_index = index
            setattr(row, 'row_type', label)
            db.session.add(row)

        elif context == AXIS_NAME_TYPES.COLUMN:
            column = TableColumn.query.get_or_404((csv_id, index))
            if label == TABLE_COLUMN_TYPES.INDEX:
                csv_file.key_column_index = index
            elif label == TABLE_COLUMN_TYPES.GROUP:
                csv_file.group_column_index = index
            setattr(column, 'column_type', label)
            db.session.add(column)
    db.session.add(csv_file)
    try:
        db.session.commit()
        return jsonify(csv_file_schema.dump(csv_file))
    except Exception:
        db.session.rollback()
        raise


@csv_bp.route('/csv/<uuid:csv_id>/row', methods=['GET'])
def list_rows(csv_id):
    CSVFile.query.get_or_404(csv_id)  # ensure the file exists
    return jsonify(table_row_schema.dump(
        TableRow.query.filter_by(csv_file_id=csv_id),
        many=True
    ))


@csv_bp.route('/csv/<uuid:csv_id>/row/<int:row_index>', methods=['GET'])
def get_row(csv_id, row_index):
    return jsonify(table_row_schema.dump(
        TableRow.query.get_or_404((csv_id, row_index))
    ))


@csv_bp.route('/csv/<uuid:csv_id>/plot/pca', methods=['GET'])
def get_pca_plot(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    max_components = int(request.args.get('max_components', 5))
    fatal_errors = get_fatal_index_errors(csv_file)
    if fatal_errors:
        return jsonify({
            'error': 'Fatal error in table validation',
            'validation': validation_schema.dump(fatal_errors, many=True)
        }), 400
    try:
        table = csv_file.apply_transforms()
    except OpenCPUException as e:
        if e.response is None:
            return jsonify({
                'error': 'OpenCPU call failed',
                'method': e.method,
                'response': 'Connection failed'
            }), 504
        else:
            return jsonify({
                'error': 'OpenCPU call failed',
                'method': e.method,
                'response': e.response.content.decode()
            }), 502

    data = pca(table, max_components)

    # insert per row label metadata information
    labels = csv_file.sample_metadata
    groups = csv_file.groups
    data['labels'] = pandas.concat([groups, labels], axis=1).to_dict('list')

    return jsonify(data), 200


@csv_bp.route('/csv/<uuid:csv_id>/pca-overview', methods=['GET'])
def get_pca_overview(csv_id):
    csv_file = CSVFile.query.get_or_404(csv_id)
    png_content = opencpu.generate_image('/metabulo/R/pca_overview_plot', csv_file.table)
    return Response(png_content, mimetype='image/png')
