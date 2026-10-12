"""Public validation messages; never interpolate rejected input or secrets."""


def validation_message(error):
    kind = error.get('type', '')
    context = error.get('ctx') or {}
    if kind == 'value_error':
        return error.get('msg', 'Valor no válido').removeprefix('Value error, ')
    messages = {
        'missing': 'Este campo es obligatorio', 'extra_forbidden': 'Campo no admitido',
        'int_parsing': 'Escribe un número entero', 'int_type': 'Escribe un número entero',
        'int_from_float': 'No se admiten fracciones', 'float_parsing': 'Escribe un número válido',
        'bool_parsing': 'Elige sí o no', 'string_type': 'Escribe un texto',
        'literal_error': 'Elige una de las opciones permitidas', 'enum': 'Opción no permitida',
        'datetime_from_date_parsing': 'Fecha y hora no válidas', 'json_invalid': 'Formato JSON no válido',
    }
    for code, text, key in [('greater_than_equal', 'El mínimo permitido es', 'ge'), ('less_than_equal', 'El máximo permitido es', 'le'), ('string_too_short', 'Longitud mínima:', 'min_length'), ('string_too_long', 'Longitud máxima:', 'max_length'), ('too_long', 'Máximo de elementos:', 'max_length')]:
        if kind == code:
            return f'{text} {context.get(key)}'
    return messages.get(kind, 'Valor no válido; revisa el formato y los límites del campo')
