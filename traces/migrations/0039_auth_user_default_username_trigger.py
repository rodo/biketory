from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("traces", "0038_add_surface_extracted_status"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""\
CREATE OR REPLACE FUNCTION set_default_username()
RETURNS TRIGGER AS $$
BEGIN
  NEW.username := 'user' || NEW.id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auth_user_default_username
  BEFORE INSERT ON auth_user
  FOR EACH ROW
  EXECUTE FUNCTION set_default_username();
""",
            reverse_sql="""\
DROP TRIGGER IF EXISTS trg_auth_user_default_username ON auth_user;
DROP FUNCTION IF EXISTS set_default_username();
""",
        ),
    ]
