from django.db import migrations


def repair_fee_schema(apps, schema_editor):
    connection = schema_editor.connection
    introspection = connection.introspection

    def table_exists(table_name):
        return table_name in introspection.table_names()

    def column_names(table_name):
        with connection.cursor() as cursor:
            return {column.name for column in introspection.get_table_description(cursor, table_name)}

    models_to_create = [
        ("FeeLedger", "FeeLedger"),
        ("FeeStructure", "FeeStructure"),
        ("FeeInvoice", "FeeInvoice"),
        ("StudentFeeAccount", "StudentFeeAccount"),
        ("FeePayment", "FeePayment"),
    ]

    for _, model_name in models_to_create:
        model = apps.get_model("fees", model_name)
        table_name = model._meta.db_table
        if not table_exists(table_name):
            schema_editor.create_model(model)

    for _, model_name in models_to_create:
        model = apps.get_model("fees", model_name)
        table_name = model._meta.db_table
        if not table_exists(table_name):
            continue

        existing_columns = column_names(table_name)
        for field in model._meta.local_fields:
            if field.name == "id" or field.many_to_many:
                continue
            if field.column in existing_columns:
                continue
            schema_editor.add_field(model, field)


class Migration(migrations.Migration):
    dependencies = [
        ("fees", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(repair_fee_schema, migrations.RunPython.noop),
    ]
