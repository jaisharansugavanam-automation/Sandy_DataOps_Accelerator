CREATE OR REPLACE TABLE collaborators (
    collaborator_name STRING,
    role STRING,
    date_of_start DATE
);

INSERT INTO collaborators (collaborator_name, role, date_of_start) VALUES
    ('Jaisharan Sugavanam', 'Data Engineer', CURRENT_DATE),
    ('Athish', 'Intern', CURRENT_DATE);
