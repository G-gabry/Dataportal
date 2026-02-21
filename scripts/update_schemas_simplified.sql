-- Migration: Simplify item schemas to Name, URL, Country, Summary
-- Run this against the Cloud SQL database to update schemas

-- Update PROGRAM schema
UPDATE item_schemas
SET schema_json = '{
    "fields": {
        "name": {"type": "string", "required": true, "description": "Name of the program"},
        "url": {"type": "url", "required": true, "description": "Direct URL to the program page"},
        "country": {"type": "string", "required": true, "description": "Country where the program is offered"},
        "summary": {"type": "text", "required": true, "description": "Brief summary of the program (2-3 sentences)"}
    }
}',
extraction_prompt = 'Extract the following information from this page:
- name: The full name of the academic program
- url: The direct URL to this program page
- country: The country where this program is offered
- summary: A brief 2-3 sentence summary describing the program

Return as JSON. If information is not available, use null.'
WHERE item_type = 'PROGRAM';

-- Update SCHOLARSHIP schema
UPDATE item_schemas
SET schema_json = '{
    "fields": {
        "name": {"type": "string", "required": true, "description": "Name of the scholarship"},
        "url": {"type": "url", "required": true, "description": "Direct URL to the scholarship page"},
        "country": {"type": "string", "required": true, "description": "Country or countries where scholarship applies"},
        "summary": {"type": "text", "required": true, "description": "Brief summary of the scholarship (2-3 sentences)"}
    }
}',
extraction_prompt = 'Extract the following information from this page:
- name: The full name of the scholarship or funding opportunity
- url: The direct URL to this scholarship page
- country: The country/countries where this scholarship can be used
- summary: A brief 2-3 sentence summary describing the scholarship and its benefits

Return as JSON. If information is not available, use null.'
WHERE item_type = 'SCHOLARSHIP';

-- Update CONFERENCE schema
UPDATE item_schemas
SET schema_json = '{
    "fields": {
        "name": {"type": "string", "required": true, "description": "Name of the conference"},
        "url": {"type": "url", "required": true, "description": "Direct URL to the conference page"},
        "country": {"type": "string", "required": true, "description": "Country where the conference is held"},
        "summary": {"type": "text", "required": true, "description": "Brief summary of the conference (2-3 sentences)"}
    }
}',
extraction_prompt = 'Extract the following information from this page:
- name: The full name of the conference or event
- url: The direct URL to this conference page
- country: The country where the conference is being held
- summary: A brief 2-3 sentence summary describing the conference topic and dates

Return as JSON. If information is not available, use null.'
WHERE item_type = 'CONFERENCE';

-- Update EXCHANGE schema
UPDATE item_schemas
SET schema_json = '{
    "fields": {
        "name": {"type": "string", "required": true, "description": "Name of the exchange program"},
        "url": {"type": "url", "required": true, "description": "Direct URL to the exchange program page"},
        "country": {"type": "string", "required": true, "description": "Host country for the exchange"},
        "summary": {"type": "text", "required": true, "description": "Brief summary of the exchange program (2-3 sentences)"}
    }
}',
extraction_prompt = 'Extract the following information from this page:
- name: The full name of the exchange program
- url: The direct URL to this exchange program page
- country: The host country for this exchange
- summary: A brief 2-3 sentence summary describing the exchange program

Return as JSON. If information is not available, use null.'
WHERE item_type = 'EXCHANGE';

-- Verify the updates
SELECT item_type, schema_json FROM item_schemas;
