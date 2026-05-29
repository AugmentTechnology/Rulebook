from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
import requests
import os
from datetime import datetime
from itertools import zip_longest
from psycopg2.extras import RealDictCursor
import uuid
from werkzeug.utils import secure_filename


app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/rulebook/static/css/"
)
BLOCK_FIELDS = [
    # -------- FILE DOWNLOADING PROCESS --------
    ("file_downloading_process", "office_superbill_scans", "office_superbill"),
    ("file_downloading_process", "nursing_peritoneal_dialysis_superbills_scans", "nursing_pd_superbill"),
    ("file_downloading_process", "hospital_superbill_scans", "hospital_superbill"),
    ("file_downloading_process", "dialysis_billing_scans", "dialysis_scans"),
    ("file_downloading_process", "eob_scans", "eob_scans"),
    ("file_downloading_process", "other_correspondence_scans", "other_correspondence"),

    # -------- DEMO CHARGE ENTRY PROCESS --------
    ("demo_charge_entry_process", "scheduling", "scheduling"),
    ("demo_charge_entry_process", "office_demographics", "office_demographics"),
    ("demo_charge_entry_process", "office_charges_entry", "office_charges"),
    ("demo_charge_entry_process", "office_authorization", "office_authorization"),
    ("demo_charge_entry_process", "hospital_charges", "hospital_charges"),
    ("demo_charge_entry_process", "dialysis_charge_entry_process", "dialysis_charge_entry"),

    # -------- CODING --------
    ("coding", "office_rule", "office_coding_rule"),
    ("coding", "office_cpt_rule", "office_coding_cpt_rule"),
    ("coding", "hospital_rule", "hospital_coding_rule"),
    ("coding", "hospital_cpt_rule", "hospital_coding_cpt_rule"),
    ("coding", "nursing_rule", "nursing_coding_rule"),
    ("coding", "nursing_cpt_rule", "nursing_coding_cpt_rule"),
    ("coding", "dialysis_rule", "dialysis_coding_rule"),
    ("coding", "dialysis_cpt_rule", "dialysis_coding_cpt_rule"),

    # -------- TOP DENIALS AND ACTIONS --------
    ("top_denials_and_actions", "auth", "auth"),
    ("top_denials_and_actions", "authorization_category", "authorization_category"),
    ("top_denials_and_actions", "medical_record_request", "medical_record_request"),
    ("top_denials_and_actions", "medical_records_insufficient", "medical_records_insufficient"),
    ("top_denials_and_actions", "overpayment_request", "overpayment_request"),
    ("top_denials_and_actions", "coverage_issue", "coverage_issue"),
    ("top_denials_and_actions", "coverage_issue_category", "coverage_issue_category"),
    ("top_denials_and_actions", "inconsistent_dx", "inconsistent_dx"),
    ("top_denials_and_actions", "hospice", "hospice"),
    ("top_denials_and_actions", "primary_paid_more_than_sec_allowable", "primary_paid_more_than_sec_allowable"),
    ("top_denials_and_actions", "non_par_out_of_network", "non_par_out_of_network"),
    ("top_denials_and_actions", "non_par_out_of_network_category", "non_par_out_of_network_category"),
    ("top_denials_and_actions", "time_filing_limits", "time_filing_limits"),
    ("top_denials_and_actions", "inclusive", "inclusive"),

    # -------- BILLING PROTOCOLS --------
    ("billing_protocols", "patient_payment_confirmation_method", "payment_confirm"),

    # -------- COLLECTION / MEETING REPORTS --------
    ("collection_agency_and_insurance_logins", "standard_monthly_reports", "monthly_reports"),
    ("collection_agency_and_insurance_logins", "custom_client_reports", "custom_reports"),
    ("collection_agency_and_insurance_logins", "required_meeting_participants", "meeting_participants"),
    ("collection_agency_and_insurance_logins", "meeting_frequency", "meeting_frequency"),
    ("collection_agency_and_insurance_logins", "meeting_mode", "meeting_mode"),
]

# ---------------- DB CONNECTION ----------------
def get_db_connection():
    return psycopg2.connect(
        host="192.168.15.10",
        port="2602",
        database="base_data",
        user="postgres",
        password="12345678"
    )

# ---------------- DOMAIN HELPERS ----------------
Software_MAP = {
    'ecw': 'eclinicalworks.com',
    'eclinicalworks': 'eclinicalworks.com',
    'tebra': 'tebra.com'
}

INSURANCE_MAP = {
    'aetna': 'aetna.com',
    'cigna': 'cigna.com',
    'uhc': 'uhc.com',
    'bcbs': 'bcbs.com',
    'humana': 'humana.com',
    'medicare': 'medicare.gov'
}

def get_software_domain(name):
    if not name:
        return ""
    clean = name.strip().lower()
    return Software_MAP.get(clean, f"{clean.replace(' ', '')}.com")

def get_insurance_domain(name):
    if not name:
        return ""
    clean = name.strip().lower()
    return INSURANCE_MAP.get(clean, f"{clean.replace(' ', '')}.com")


# ---------------- SELECT PRACTICE ----------------
@app.route('/rulebook/', methods=['GET'])
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT practice_id, practice_name
        FROM practice_information
        ORDER BY practice_name
    """)
    practices = [{"practice_id": r[0], "practice_name": r[1]} for r in cur.fetchall()]
    cur.close()
    conn.close()

    return render_template("index.html", practices=practices)


@app.route('/rulebook/select_practice', methods=['POST'])
def select_practice():
    practice_id = request.form.get('practice_id')

    if practice_id == "NEW":
        return redirect(url_for('new_practice'))

    return redirect(url_for('rulebook', practice_id=practice_id))
   


@app.route('/rulebook/new_practice', methods=['GET'])
def new_practice():
    empty_facilities = {
        "office": [],
        "hospital": [],
        "nursing": [],
        "surgery": [],
        "dialysis": [],
        "cathlab": [],
    }

    return render_template(
        'details.html',
        mode='edit',
        is_new=True,
        practice_id=None,

        details={},
        office_contacts={},
        provider_information={},
        practice_providers=[],
        communication_method={},
        practice_software_systems={},
        facilities=empty_facilities,
        hospital_volume={},
        insurance_details={},
        insurance_procedure=[],
        services_procedure={},
        immun_procedure={},
        billing_protocols={},
        clearinghouse_eob_details={},
        collection_agency_and_insurance_logins={},
        practice_images={},
        get_domain=get_insurance_domain,
        file_downloading_process={},
        demo_charge_entry_process={},
        coding_by_facility={},
        top_denials_and_actions={},
        patient_statement_process={},
        generate_balance_blocks=[],
        review_checklist_blocks=[],
        block_data={}
    )
@app.route("/rulebook/delete-block/<int:block_id>", methods=["POST"])
def delete_block(block_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # First get block details so we can also hide its images
    cur.execute("""
        SELECT practice_id, section_key, field_key, block_order
        FROM rulebook_field_blocks
        WHERE id = %s
    """, (block_id,))

    block = cur.fetchone()

    if not block:
        cur.close()
        conn.close()
        return jsonify({"success": False, "message": "Block not found"}), 404

    practice_id, section_key, field_key, block_order = block

    # Soft delete block
    cur.execute("""
        UPDATE rulebook_field_blocks
        SET isactive = false,
            modified_at = NOW()
        WHERE id = %s
    """, (block_id,))

    # Soft delete linked images for same block
    cur.execute("""
        UPDATE practice_images
        SET isactive = false
        WHERE practice_id = %s
          AND section_key = %s
          AND field_key = %s
          AND block_order = %s
    """, (practice_id, section_key, field_key, block_order))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"success": True})

@app.route("/rulebook/create-full", methods=["POST"])
def create_practice_full():
    conn = get_db_connection()
    cur = conn.cursor()

    practice_name = (request.form.get("practice_name") or "").strip()

    if not practice_name:
        cur.close()
        conn.close()
        return "Practice name is required", 400

    cur.execute("""
        INSERT INTO practice_information (practice_name)
        VALUES (%s)
        RETURNING practice_id
    """, (practice_name,))

    new_practice_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return save_practice(new_practice_id)

@app.route("/rulebook/<int:practice_id>")
def rulebook(practice_id):
    print("RULEBOOK PAGE OPENED")
    conn = get_db_connection()
    cur = conn.cursor()

   

    cur.execute("""
        SELECT *
        FROM practice_information
        WHERE practice_id = %s
    """, (practice_id,))


    row = cur.fetchone()
    columns = [desc[0] for desc in cur.description]
    
    

    if not row:
        return "Practice not found", 404

    details = dict(zip(columns, row))

    # -------- OFFICE CONTACTS READ --------
    cur.execute("""
        SELECT *
        FROM office_contacts
        WHERE practice_id = %s
    """, (practice_id,))

    office_row = cur.fetchone()
    office_cols = [desc[0] for desc in cur.description]

    office_contacts = dict(zip(office_cols, office_row)) if office_row else {}

   # ---------------- PROVIDER INFORMATION (single row) ----------------
    cur.execute("""
        SELECT *
        FROM provider_information
        WHERE practice_id = %s
    """, (practice_id,))
    provider_row = cur.fetchone()
    provider_cols = [desc[0] for desc in cur.description]
    provider_information = dict(zip(provider_cols, provider_row)) if provider_row else {}

    # ---------------- PRACTICE PROVIDERS (multiple rows) ----------------
    cur.execute("""
        SELECT provider_id, provider_name, provider_npi
        FROM practice_providers
        WHERE practice_id = %s
        ORDER BY provider_id
    """, (practice_id,))
    practice_providers = [
        {
            "provider_id": r[0],
            "provider_name": r[1],
            "provider_npi": r[2]
        }
        for r in cur.fetchall()
    ]
    
    # -------- COMMUNICATION METHOD READ --------
    cur.execute("""
        SELECT *
        FROM communication_method
        WHERE practice_id = %s
    """, (practice_id,))

    comm_row = cur.fetchone()
    comm_cols = [desc[0] for desc in cur.description]
    communication_method = dict(zip(comm_cols, comm_row)) if comm_row else {}

    # -------- PRACTICE SOFTWARE & SYSTEMS READ --------
    cur.execute("""
        SELECT
            clinical_software_name,
            clinical_software_login_access,
            billing_software_name,
            tebra_location,
            billing_software_login_access
        FROM practice_software_systems
        WHERE practice_id = %s
    """, (practice_id,))

    row = cur.fetchone()

    practice_software_systems = {
        "clinical_software_name": row[0],
        "clinical_software_login_access": row[1],
        "billing_software_name": row[2],
        "tebra_location": row[3],
        "billing_software_login_access": row[4],
    } if row else {}


    cur.execute("""
    SELECT facility_id, facility_type, facility_name, facility_address, facility_npi, login_access, daily_number_claims, monthly_number_claims, first_date_of_service
    FROM participating_facilities
    WHERE practice_id = %s
    ORDER BY facility_id
    """, (practice_id,))

    rows = cur.fetchall()

    facilities = {
        "office": [],
        "hospital": [],
        "nursing": [],
        "surgery": [],
        "dialysis": [],
        "cathlab": [],
    }

    for facility_id, facility_type, name, address, npi, login_access, daily_claims, monthly_claims, first_dos in rows:
        facilities.setdefault(facility_type, []).append({
            "facility_id": facility_id,
            "facility_name": name or "",
            "facility_address": address or "",
            "facility_npi": npi or "",
            "login_access": login_access or "",
            "daily_number_claims": daily_claims or "",
            "monthly_number_claims": monthly_claims or "",
            "first_date_of_service": first_dos or "",
        })

    hospital_volume = facilities["hospital"][0] if facilities["hospital"] else {}

  
     # -------- INSURANCE DETAILS--------
   
    cur.execute("""
        SELECT *
        FROM insurance_details
        WHERE practice_id = %s
    """, (practice_id,))
    ins_row = cur.fetchone()
    ins_cols = [d[0] for d in cur.description] if ins_row else []
    insurance_details = dict(zip(ins_cols, ins_row)) if ins_row else {}


    # -------- INSURANCE PROCEDURE --------
  
    cur.execute("""
    SELECT procedure_code, procedure_fee
    FROM insurance_procedure
    WHERE practice_id = %s
    ORDER BY id
    """, (practice_id,))

    insurance_procedure = [{"procedure_code": r[0], "procedure_fee": r[1]} for r in cur.fetchall()]

    # -------- SERVICES PROCEDURE --------

    cur.execute("""
    SELECT category, cptcode, cptdesc
    FROM services_procedures
    WHERE practice_id = %s
    """, (practice_id,))

    sp_map = {r[0]: {"cptcode": r[1] or "", "cptdesc": r[2] or ""} for r in cur.fetchall()}

    services_procedure = sp_map.get("services", {"cptcode": "", "cptdesc": ""})
    immun_procedure    = sp_map.get("immunizations", {"cptcode": "", "cptdesc": ""})

     # -------- BILLING PROTOCOLS  --------
    cur.execute("SELECT * FROM billing_protocols WHERE practice_id = %s", (practice_id,))
    bp_row = cur.fetchone()
    bp_cols = [d[0] for d in cur.description] if bp_row else []
    billing_protocols = dict(zip(bp_cols, bp_row)) if bp_row else {}

    # -------- CLEARNING HOUSE AND EOB DETAILS --------

    cur.execute("""
    SELECT practice_id,
           clearinghouse_name,
           site_id,
           has_clearinghouse_login,
           eras_received_in_system,
           eras_not_received,
           paper_eobs_received,
           paper_eob_receive_method,
           attach_eobs_to_patient_accounts,
           dummy_patient_name,
           payment_posting_frequency,
           key_notes_for_us_rep,
           statement_frequency,
           minimum_balance_rule,
           customized_statement_print_steps
    FROM clearinghouse_eob_details
    WHERE practice_id = %s
    """, (practice_id,))

    row = cur.fetchone()
    cols = [desc[0] for desc in cur.description]
    clearinghouse_eob_details = dict(zip(cols, row)) if row else {}

    cur.execute("""
    SELECT
        practice_id,
        has_collection_agency,
        collection_agency_name,
        collection_agency_login_access,
        insurance_with_login_access,
        has_insurance_login_access,
        standard_monthly_reports,
        custom_client_reports,
        required_meeting_participants,
        meeting_frequency,
        meeting_mode,
        last_sent_to_client,
        last_response_received_from_client,
        response_received_type
    FROM collection_agency_and_insurance_logins
    WHERE practice_id = %s
    """, (practice_id,))
    row = cur.fetchone()

    collection_agency_and_insurance_logins = {}
    if row:
        collection_agency_and_insurance_logins = {
            "practice_id": row[0],
            "has_collection_agency": row[1],
            "collection_agency_name": row[2] or "",
            "collection_agency_login_access": row[3] or "",
            "insurance_with_login_access": row[4] or "",
            "has_insurance_login_access": row[5],
            "standard_monthly_reports": row[6] or "",
            "custom_client_reports": row[7] or "",
            "required_meeting_participants": row[8] or "",
            "meeting_frequency": row[9] or "",
            "meeting_mode": row[10] or "",
            "last_sent_to_client": row[11] or "",
            "last_response_received_from_client": row[12] or "",
            "response_received_type": row[13] or "",
        }

    cur.execute("""
      SELECT section_key, field_key, block_order, file_name
      FROM practice_images
      WHERE practice_id = %s
        AND COALESCE(isactive, true) = true
      ORDER BY created_at ASC
    """, (practice_id,))

    rows = cur.fetchall()

    practice_images = {}

    for s, f, block_order, fn in rows:
        key = str(block_order) if block_order is not None else "0"
        practice_images.setdefault(s, {}).setdefault(f, {}).setdefault(key, []).append(fn)

    cur.execute("""
        SELECT *
        FROM file_downloading_process
        WHERE practice_id = %s
    """, (practice_id,))

    fdp_row = cur.fetchone()
    fdp_cols = [desc[0] for desc in cur.description]

    file_downloading_process = dict(zip(fdp_cols, fdp_row)) if fdp_row else {}

    cur.execute("""
    SELECT *
    FROM demo_charge_entry_process
    WHERE practice_id = %s
    """, (practice_id,))

    dcep_row = cur.fetchone()
    dcep_cols = [desc[0] for desc in cur.description]

    demo_charge_entry_process = dict(zip(dcep_cols, dcep_row)) if dcep_row else {}

    # -------- CODING READ --------

    cur.execute("""
        SELECT rule, cpt_rule
        FROM coding
        WHERE practice_id = %s
          AND COALESCE(isactive, true) = true
        ORDER BY 
            CASE WHEN facility_type = 'general' THEN 0 ELSE 1 END,
            id
        LIMIT 1
    """, (practice_id,))

    coding_row = cur.fetchone()

    coding_by_facility = {
        "general": {
            "rule": coding_row[0] if coding_row else "",
            "cpt_rule": coding_row[1] if coding_row else ""
        }
    }

    cur.execute("""
        SELECT *
        FROM top_denials_and_actions
        WHERE practice_id = %s
    """, (practice_id,))

    top_denials_row = cur.fetchone()
    top_denials_cols = [desc[0] for desc in cur.description]

    top_denials_and_actions = dict(zip(top_denials_cols, top_denials_row)) if top_denials_row else {}

    # -------- PATIENT STATEMENT PROCESS READ --------
    cur.execute("""
        SELECT *
        FROM patient_statement_process
        WHERE practice_id = %s
    """, (practice_id,))

    ps_row = cur.fetchone()
    ps_cols = [desc[0] for desc in cur.description]
    patient_statement_process = dict(zip(ps_cols, ps_row)) if ps_row else {}

    # -------- BLOCKS FOR generate_patient_balance_list --------
    generate_balance_blocks = read_field_blocks(
        cur,
        practice_id,
        "patient_statement_process",
        "generate_patient_balance_list"
    )

    review_checklist_blocks = read_field_blocks(
        cur,
        practice_id,
        "patient_statement_process",
        "patient_statement_review_checklist"
    )

    block_data = {}

    for section, field, prefix in BLOCK_FIELDS:
        block_data[f"{prefix}_blocks"] = read_field_blocks(
            cur,
            practice_id,
            section,
            field
        )
    cur.close()
    conn.close()

    template_name = "details_pdf.html" if request.args.get("pdf") == "1" else "details.html"
    return render_template(
        template_name,
        details=details,
        practice_id=practice_id,
        office_contacts=office_contacts,
        provider_information=provider_information,
        practice_providers=practice_providers,
        communication_method=communication_method,
        practice_software_systems=practice_software_systems,
        facilities=facilities,
        hospital_volume=hospital_volume,
        insurance_details=insurance_details,
        insurance_procedure=insurance_procedure,
        services_procedure=services_procedure,
        immun_procedure=immun_procedure,
        billing_protocols=billing_protocols,
        clearinghouse_eob_details=clearinghouse_eob_details,
        collection_agency_and_insurance_logins=collection_agency_and_insurance_logins,
        practice_images=practice_images,
        get_domain=get_insurance_domain,
        file_downloading_process=file_downloading_process,
        demo_charge_entry_process=demo_charge_entry_process,
        coding_by_facility=coding_by_facility,
        top_denials_and_actions=top_denials_and_actions,
        patient_statement_process=patient_statement_process,
        generate_balance_blocks=generate_balance_blocks,
        review_checklist_blocks=review_checklist_blocks,
        block_data=block_data
    )


@app.route("/rulebook/create", methods=["GET", "POST"])
def create_practice():
    if request.method == "POST":
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO practice_information (practice_name)
            VALUES (%s)
            RETURNING practice_id
        """, (request.form.get("practice_name"),))

        practice_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("rulebook", practice_id=practice_id))

    return render_template("create_practice.html")


@app.route("/rulebook/save/<int:practice_id>", methods=["POST"])
def save_practice(practice_id):
    data = request.form
    raw_date = data.get("billing_start_date")
    billing_start_date = None

    if raw_date:
        try:
           billing_start_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
        except ValueError:
            billing_start_date = None
    def clean(v):
        v = (v or "").strip()
        return v if v else None

    values = {
        "practice_id": practice_id,
        "practice_name": clean(data.get("practice_name")),
        "billing_start_date": clean(data.get("billing_start_date")),
        "specialty": clean(data.get("specialty")),
        "practice_address": clean(data.get("practice_address")),
        "practice_phone": clean(data.get("practice_phone")),
        "practice_tax_id": clean(data.get("practice_tax_id")),
        "practice_npi": clean(data.get("practice_npi")),
        "email": clean(data.get("email")),
    }

    conn = get_db_connection()
    cur = conn.cursor()

    # Upsert (recommended): insert if missing, else update
    cur.execute("""
        INSERT INTO practice_information (
            practice_id,
            practice_name,
            billing_start_date,
            specialty,
            practice_address,
            practice_phone,
            practice_tax_id,
            practice_npi,
            email
           
        )
        VALUES (
            %(practice_id)s,
            %(practice_name)s,
            %(billing_start_date)s,
            %(specialty)s,
            %(practice_address)s,
            %(practice_phone)s,
            %(practice_tax_id)s,
            %(practice_npi)s,
            %(email)s
        
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            practice_name = EXCLUDED.practice_name,
            billing_start_date = EXCLUDED.billing_start_date,
            specialty = EXCLUDED.specialty,
            practice_address = EXCLUDED.practice_address,
            practice_phone = EXCLUDED.practice_phone,
            practice_tax_id = EXCLUDED.practice_tax_id,
            practice_npi = EXCLUDED.practice_npi,
            email = EXCLUDED.email
           
    """, values)

    # -------- OFFICE CONTACTS SAVE --------

    office_values = {
        "practice_id": practice_id,
        "provider_poc_name": clean(data.get("provider_poc_name")),
        "provider_poc_email": clean(data.get("provider_poc_email")),
        "provider_poc_phone": clean(data.get("provider_poc_phone")),
        "provider_poc_fax": clean(data.get("provider_poc_fax")),
        "provider_poc_designation": clean(data.get("provider_poc_designation")),
        "billing_rep_name": clean(data.get("billing_rep_name")),
        "billing_rep_email": clean(data.get("billing_rep_email")),
        "billing_rep_phone": clean(data.get("billing_rep_phone")),
        "billing_rep_ext": clean(data.get("billing_rep_ext")),
        "billing_rep_direct_line": clean(data.get("billing_rep_direct_line")),
        "billing_rep_fax": clean(data.get("billing_rep_fax")),
        "offshore_team_lead":clean(data.get("offshore_team_lead")),
        "offshore_team_manager": clean(data.get("offshore_team_manager"))
    }

    cur.execute("""
        INSERT INTO office_contacts (
            practice_id,
            provider_poc_name,
            provider_poc_email,
            provider_poc_phone,
            provider_poc_fax,
            provider_poc_designation,
            billing_rep_name,
            billing_rep_email,
            billing_rep_phone,
            billing_rep_ext,
            billing_rep_direct_line,
            billing_rep_fax,
            offshore_team_lead,
            offshore_team_manager
           
        )
        VALUES (
            %(practice_id)s,
            %(provider_poc_name)s,
            %(provider_poc_email)s,
            %(provider_poc_phone)s,
            %(provider_poc_fax)s,
            %(provider_poc_designation)s,
            %(billing_rep_name)s,
            %(billing_rep_email)s,
            %(billing_rep_phone)s,
            %(billing_rep_ext)s,
            %(billing_rep_direct_line)s,
            %(billing_rep_fax)s,
            %(offshore_team_lead)s,
            %(offshore_team_manager)s
          
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            provider_poc_name = EXCLUDED.provider_poc_name,
            provider_poc_email = EXCLUDED.provider_poc_email,
            provider_poc_phone = EXCLUDED.provider_poc_phone,
            provider_poc_fax = EXCLUDED.provider_poc_fax,
            provider_poc_designation = EXCLUDED.provider_poc_designation,
            billing_rep_name = EXCLUDED.billing_rep_name,
            billing_rep_email = EXCLUDED.billing_rep_email,
            billing_rep_phone = EXCLUDED.billing_rep_phone,
            billing_rep_ext = EXCLUDED.billing_rep_ext,
            billing_rep_direct_line = EXCLUDED.billing_rep_direct_line,
            billing_rep_fax = EXCLUDED.billing_rep_fax,
            offshore_team_lead = EXCLUDED.offshore_team_lead,
            offshore_team_manager = EXCLUDED.offshore_team_manager
           
    """, office_values)
    # -------- PROVIDER INFORMATION SAVE --------
    provider_count = request.form.get("provider_count")

    cur.execute("""
        INSERT INTO provider_information (
            practice_id,
            provider_count
         
        )
        VALUES (
            %s,
            %s
         
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            provider_count = EXCLUDED.provider_count
            
    """, (
        practice_id,
        provider_count if provider_count else None
    ))

    # -------- PRACTICE PROVIDERS SAVE (MULTIPLE ROWS) --------

    # Remove existing providers for this practice (clean replace)
    cur.execute(
        "DELETE FROM practice_providers WHERE practice_id = %s",
        (practice_id,)
    )

    provider_names = request.form.getlist("provider_name")
    provider_npis = request.form.getlist("provider_npi")

    for name, npi in zip(provider_names, provider_npis):
        if not name and not npi:
            continue  # skip empty rows

        cur.execute("""
            INSERT INTO practice_providers (
                practice_id,
                provider_name,
                provider_npi
               
            )
            VALUES (%s, %s, %s)
        """, (
            practice_id,
            name.strip() if name else None,
            npi.strip() if npi else None
        ))

        # ---------------- COMMUNICATION METHOD UPSERT ----------------
    cur.execute("""
        INSERT INTO communication_method (
            practice_id,
            communication_method,
            oplist_frequency,
            delivery_mode,
            email_or_fax,
            oplist_delivery_method
        
        )
        VALUES (
            %(practice_id)s,
            %(communication_method)s,
            %(oplist_frequency)s,
            %(delivery_mode)s,
            %(email_or_fax)s,
            %(oplist_delivery_method)s
         
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            communication_method      = EXCLUDED.communication_method,
            oplist_frequency          = EXCLUDED.oplist_frequency,
            delivery_mode             = EXCLUDED.delivery_mode,
            email_or_fax              = EXCLUDED.email_or_fax,
            oplist_delivery_method    = EXCLUDED.oplist_delivery_method
         
    """, {
        "practice_id": practice_id,
        "communication_method": data.get("communication_method"),
        "oplist_frequency": data.get("oplist_frequency"),
        "delivery_mode": data.get("delivery_mode"),
        "email_or_fax": data.get("email_or_fax"),
        "oplist_delivery_method": data.get("oplist_delivery_method"),
    })


    # -------- PRACTICE SOFTWARE & SYSTEMS SAVE --------

    cur.execute("""
        INSERT INTO practice_software_systems (
            practice_id,
            clinical_software_name,
            clinical_software_login_access,
            billing_software_name,
            tebra_location,
            billing_software_login_access
           
        )
        VALUES (
            %(practice_id)s,
            %(clinical_software_name)s,
            %(clinical_software_login_access)s,
            %(billing_software_name)s,
            %(tebra_location)s,
            %(billing_software_login_access)s
           
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            clinical_software_name = EXCLUDED.clinical_software_name,
            clinical_software_login_access = EXCLUDED.clinical_software_login_access,
            billing_software_name = EXCLUDED.billing_software_name,
            tebra_location = EXCLUDED.tebra_location,
            billing_software_login_access = EXCLUDED.billing_software_login_access
            
    """, {
        "practice_id": practice_id,
        "clinical_software_name": clean(data.get("clinical_software_name")),
        "clinical_software_login_access": clean(data.get("clinical_software_login_access")),
        "billing_software_name": clean(data.get("billing_software_name")),
        "tebra_location": clean(data.get("tebra_location")),
        "billing_software_login_access": clean(data.get("billing_software_login_access"))
    })


    #------------------- PARTICIPATING FACILITIES --------------------
    cur.execute("DELETE FROM participating_facilities WHERE practice_id = %s", (practice_id,))

    def split_lines_keep_rows(field_name):
        """
        Supports BOTH input styles:
        1) Add-row inputs: name="hospital_name[]" multiple inputs -> getlist() returns many items
        2) Single textarea: name="hospital_name[]" one textarea -> getlist() returns [ "line1\nline2\n..." ]
           In that case, split into multiple rows.
        """
        vals = request.form.getlist(field_name)

        # textarea case -> one item with newlines
        if len(vals) == 1:
            vals = (vals[0] or "").splitlines()

        # clean each row
        out = []
        for v in vals:
            v = (v or "").strip()
            out.append(v)
        return out

    def one_line(v):
        # keep for fields that MUST be single-line per row (name/address)
        lines = (v or "").splitlines()

        if not lines:
            return None

        v = lines[0].strip()
        return v if v else None

    def npi_10(v):
        # NPI must be max 10 digits
        lines = (v or "").splitlines()

        if not lines:
            return None

        v = lines[0].strip()

        if not v:
            return None

        digits = "".join(ch for ch in v if ch.isdigit())
        return digits[:10] if digits else None

    def ins_facility(ftype, name, address=None, npi=None, login=None, daily_claims=None, monthly_claims=None, first_dos=None):
        name1 = one_line(name)
        addr1 = one_line(address)
        npi1 = npi_10(npi)

        login1 = (login or "").strip()
        login1 = login1 if login1 else None

        daily_claims = (daily_claims or "").strip()
        monthly_claims = (monthly_claims or "").strip()
        first_dos = (first_dos or "").strip()

        daily_claims = daily_claims if daily_claims else None
        monthly_claims = monthly_claims if monthly_claims else None
        first_dos = first_dos if first_dos else None

        if not (name1 or addr1 or npi1 or login1 or daily_claims or monthly_claims or first_dos):
            return

        cur.execute("""
            INSERT INTO participating_facilities
                (
                    practice_id,
                    facility_type,
                    facility_name,
                    facility_address,
                    facility_npi,
                    login_access,
                    daily_number_claims,
                    monthly_number_claims,
                    first_date_of_service
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            practice_id,
            ftype,
            name1,
            addr1,
            npi1,
            login1,
            daily_claims,
            monthly_claims,
            first_dos
        ))

    # ---------------- OFFICE ----------------
    for name, address, npi, login in zip_longest(
        split_lines_keep_rows("office_name[]"),
        split_lines_keep_rows("office_address[]"),
        split_lines_keep_rows("office_npi[]"),
        split_lines_keep_rows("office_login[]"),
        fillvalue=""
    ):
        ins_facility("office", name, address, npi, login)

    # ---------------- HOSPITALS ----------------
    for name, address, npi, login, daily_claims, monthly_claims, first_dos in zip_longest(
        split_lines_keep_rows("hospital_name[]"),
        split_lines_keep_rows("hospital_address[]"),
        split_lines_keep_rows("hospital_npi[]"),
        split_lines_keep_rows("hospital_login[]"),
        split_lines_keep_rows("daily_number_claims"),
        split_lines_keep_rows("monthly_number_claims"),
        split_lines_keep_rows("first_date_of_service"),
        fillvalue=""
    ):
        ins_facility("hospital", name, address, npi, login, daily_claims, monthly_claims, first_dos)


    # ---------------- NURSING ----------------
    for name, address, npi in zip_longest(
        split_lines_keep_rows("nursing_name[]"),
        split_lines_keep_rows("nursing_address[]"),
        split_lines_keep_rows("nursing_npi[]"),
        fillvalue=""
    ):
        ins_facility("nursing", name, address, npi, None)


    # ---------------- SURGERY ----------------
    for name, npi in zip_longest(
        split_lines_keep_rows("surgery_name[]"),
        split_lines_keep_rows("surgery_npi[]"),
        fillvalue=""
    ):
        ins_facility("surgery", name, None, npi, None)


    # ---------------- DIALYSIS ----------------
    for name, npi in zip_longest(
        split_lines_keep_rows("dialysis_name[]"),
        split_lines_keep_rows("dialysis_npi[]"),
        fillvalue=""
    ):
        ins_facility("dialysis", name, None, npi, None)


    # ---------------- CATHLAB ----------------
    for name, npi in zip_longest(
        split_lines_keep_rows("cathlab_name[]"),
        split_lines_keep_rows("cathlab_npi[]"),
        fillvalue=""
    ):
        ins_facility("cathlab", name, None, npi, None)

    # -------- INSURANCE DETAILS SAVE --------

    cur.execute("""
    INSERT INTO insurance_details (
        practice_id,
        commercial,
        hmo_capitated_plans,
        ipa_name,
        ipa_email,
        ipa_phone,
        special_billing_rule_capitated,
        no_show_fee_amount,
        no_show_rule,
        new_office_visit,
        established_office_visit,
        disability_form,
        fmla_form,
        cdl_form,
        jury_form,
        others,
        self_pay_rates,
        fee_schedule_setup
    )
    VALUES (
        %(practice_id)s,
        %(commercial)s,
        %(hmo_capitated_plans)s,
        %(ipa_name)s,
        %(ipa_email)s,
        %(ipa_phone)s,
        %(special_billing_rule_capitated)s,
        %(no_show_fee_amount)s,
        %(no_show_rule)s,
        %(new_office_visit)s,
        %(established_office_visit)s,
        %(disability_form)s,
        %(fmla_form)s,
        %(cdl_form)s,
        %(jury_form)s,
        %(others)s,
        %(self_pay_rates)s,
        %(fee_schedule_setup)s
    )
    ON CONFLICT (practice_id)
    DO UPDATE SET
        commercial = EXCLUDED.commercial,
        hmo_capitated_plans = EXCLUDED.hmo_capitated_plans,
        ipa_name  = EXCLUDED.ipa_name,
        ipa_email = EXCLUDED.ipa_email,
        ipa_phone = EXCLUDED.ipa_phone,
        special_billing_rule_capitated = EXCLUDED.special_billing_rule_capitated,
        no_show_fee_amount = EXCLUDED.no_show_fee_amount,
        no_show_rule = EXCLUDED.no_show_rule,
        new_office_visit = EXCLUDED.new_office_visit,
        established_office_visit = EXCLUDED.established_office_visit,
        disability_form = EXCLUDED.disability_form,
        fmla_form = EXCLUDED.fmla_form,
        cdl_form = EXCLUDED.cdl_form,
        jury_form = EXCLUDED.jury_form,
        others = EXCLUDED.others,
        self_pay_rates = EXCLUDED.self_pay_rates,
        fee_schedule_setup = EXCLUDED.fee_schedule_setup,
modified_at = NOW()
""", {
    "practice_id": practice_id,
    "commercial": clean(data.get("commercial")),
    "hmo_capitated_plans": clean(data.get("hmo_capitated_plans")),
    "ipa_name": clean(data.get("ipa_name")),
    "ipa_email": clean(data.get("ipa_email")),
    "ipa_phone": clean(data.get("ipa_phone")),
    "special_billing_rule_capitated": clean(data.get("special_billing_rule_capitated")),
    "no_show_fee_amount": clean(data.get("no_show_fee_amount")),
    "no_show_rule": clean(data.get("no_show_rule")),
    "new_office_visit": clean(data.get("new_office_visit")),
    "established_office_visit": clean(data.get("established_office_visit")),
    "disability_form": clean(data.get("disability_form")),
    "fmla_form": clean(data.get("fmla_form")),
    "cdl_form": clean(data.get("cdl_form")),
    "jury_form": clean(data.get("jury_form")),
    "others": clean(data.get("others")),
    "self_pay_rates": clean(data.get("self_pay_rates")),
    "fee_schedule_setup": clean(data.get("fee_schedule_setup")),
})


   


    # ---------- PROCEDURE TABLE (MULTIPLE ROWS) SAVE ----------
    procedure_codes = request.form.getlist("procedure_code")
    procedure_fees  = request.form.getlist("procedure_fee")

    cur.execute("DELETE FROM insurance_procedure WHERE practice_id = %s", (practice_id,))

    for code, fee in zip(procedure_codes, procedure_fees):
        if not ((code or "").strip() or (fee or "").strip()):
            continue
        cur.execute("""
            INSERT INTO insurance_procedure (practice_id, procedure_code, procedure_fee)
            VALUES (%s, %s, %s)
        """, (practice_id, clean(code), clean(fee)))

    
    # ---------- SERVICES AND PROCEDURE ----------


    cur.execute("""
        INSERT INTO services_procedures (practice_id, category, cptcode, cptdesc)
        VALUES (%s, 'services', %s, %s)
        ON CONFLICT (practice_id, category)
        DO UPDATE SET
            cptcode = EXCLUDED.cptcode,
            cptdesc = EXCLUDED.cptdesc,
            modified_at = NOW()
    """, (
        practice_id,
        clean(request.form.get("cptcode")),
        clean(request.form.get("cptdesc"))
    ))

    cur.execute("""
        INSERT INTO services_procedures (practice_id, category, cptcode, cptdesc)
        VALUES (%s, 'immunizations', %s, %s)
        ON CONFLICT (practice_id, category)
        DO UPDATE SET
            cptcode = EXCLUDED.cptcode,
            cptdesc = EXCLUDED.cptdesc,
            modified_at = NOW()
    """, (
        practice_id,
        clean(request.form.get("cptcode1")),
        clean(request.form.get("cptdesc1"))
    ))

    # ---------- BILLING PROTOCOLS ----------
    
    bp = {
  "practice_id": practice_id,
  "charge_collection_process": clean(request.form.get("charge_collection_process")),
  "notes_locked_before_claims": (request.form.get("notes_locked_before_claims") == "Yes"),
  "notify_unlocked_notes_weekly": (request.form.get("notify_unlocked_notes_weekly") == "Yes"),
  "hold_claims_until_medicare_deductible_met": (request.form.get("hold_claims_until_medicare_deductible_met") == "Yes"),
  "remind_weekly_patient_balances": (request.form.get("remind_weekly_patient_balances") == "Yes"),
  "patient_payment_confirmation_method": clean(request.form.get("patient_payment_confirmation_method")),
  "tax_id_npi_claims_submitted_under": clean(request.form.get("tax_id_npi_claims_submitted_under")),
  "provider_type": clean(request.form.get("provider_type")),
  "mid_level_provider_names": clean(request.form.get("mid_level_provider_names")),
  "rules_for_specific_insurance_carriers": (request.form.get("rules_for_specific_insurance_carriers") == "Yes"),
  "capitation_billing_rule": clean(request.form.get("capitation_billing_rule")),
  "hospital_nursing_home_billing_rules": clean(request.form.get("hospital_nursing_home_billing_rules")),
  "immunizations_vaccines_billing_rules": clean(request.form.get("immunizations_vaccines_billing_rules")),
  "automated_email": (request.form.get("automated_email")),
}

    cur.execute("""
      INSERT INTO billing_protocols (
        practice_id,
        charge_collection_process,
        notes_locked_before_claims,
        notify_unlocked_notes_weekly,
        hold_claims_until_medicare_deductible_met,
        remind_weekly_patient_balances,
        patient_payment_confirmation_method,
        tax_id_npi_claims_submitted_under,
        provider_type,
        mid_level_provider_names,
        rules_for_specific_insurance_carriers,
        capitation_billing_rule,
        hospital_nursing_home_billing_rules,
        immunizations_vaccines_billing_rules,
        automated_email,
        modified_at
      )
      VALUES (
        %(practice_id)s,
        %(charge_collection_process)s,
        %(notes_locked_before_claims)s,
        %(notify_unlocked_notes_weekly)s,
        %(hold_claims_until_medicare_deductible_met)s,
        %(remind_weekly_patient_balances)s,
        %(patient_payment_confirmation_method)s,
        %(tax_id_npi_claims_submitted_under)s,
        %(provider_type)s,
        %(mid_level_provider_names)s,
        %(rules_for_specific_insurance_carriers)s,
        %(capitation_billing_rule)s,
        %(hospital_nursing_home_billing_rules)s,
        %(immunizations_vaccines_billing_rules)s,
        %(automated_email)s,
        NOW()
      )
      ON CONFLICT (practice_id)
      DO UPDATE SET
        charge_collection_process = EXCLUDED.charge_collection_process,
        notes_locked_before_claims = EXCLUDED.notes_locked_before_claims,
        notify_unlocked_notes_weekly = EXCLUDED.notify_unlocked_notes_weekly,
        hold_claims_until_medicare_deductible_met = EXCLUDED.hold_claims_until_medicare_deductible_met,
        remind_weekly_patient_balances = EXCLUDED.remind_weekly_patient_balances,
        patient_payment_confirmation_method = EXCLUDED.patient_payment_confirmation_method,
        tax_id_npi_claims_submitted_under = EXCLUDED.tax_id_npi_claims_submitted_under,
        provider_type = EXCLUDED.provider_type,
        mid_level_provider_names = EXCLUDED.mid_level_provider_names,
        rules_for_specific_insurance_carriers = EXCLUDED.rules_for_specific_insurance_carriers,
        capitation_billing_rule = EXCLUDED.capitation_billing_rule,
        hospital_nursing_home_billing_rules = EXCLUDED.hospital_nursing_home_billing_rules,
        immunizations_vaccines_billing_rules = EXCLUDED.immunizations_vaccines_billing_rules,
        automated_email = EXCLUDED.automated_email,
        modified_at = NOW()
    """, bp)

    # -------- CLEARINGHOUSE + EOB DETAILS SAVE --------

    def yn_bool(field_name: str):
        v = (request.form.get(field_name) or "").strip()
        if v == "Yes":
            return True
        if v == "No":
            return False
        return None

  
    ch = {
        "practice_id": practice_id,
        "clearinghouse_name": clean(request.form.get("clearinghouse_name")),
        "site_id": clean(request.form.get("site_id")),

        # BOOLEAN columns
        "has_clearinghouse_login": yn_bool("has_clearinghouse_login"),
        "attach_eobs_to_patient_accounts": yn_bool("attach_eobs_to_patient_accounts"),

        # text / multiline fields
        "eras_received_in_system": clean(request.form.get("eras_received_in_system")),
        "eras_not_received": clean(request.form.get("eras_not_received")),
        "paper_eobs_received": clean(request.form.get("paper_eobs_received")),
        "paper_eob_receive_method": clean(request.form.get("paper_eob_receive_method")),
        "dummy_patient_name": clean(request.form.get("dummy_patient_name")),
        "payment_posting_frequency": clean(request.form.get("payment_posting_frequency")),
        "key_notes_for_us_rep": clean(request.form.get("key_notes_for_us_rep")),
        "statement_frequency": clean(request.form.get("statement_frequency")),
        "minimum_balance_rule": clean(request.form.get("minimum_balance_rule")),
        "customized_statement_print_steps": clean(request.form.get("customized_statement_print_steps")),
    }

    cur.execute("""
        INSERT INTO clearinghouse_eob_details (
            practice_id,
            clearinghouse_name,
            site_id,
            has_clearinghouse_login,
            eras_received_in_system,
            eras_not_received,
            paper_eobs_received,
            paper_eob_receive_method,
            attach_eobs_to_patient_accounts,
            dummy_patient_name,
            payment_posting_frequency,
            key_notes_for_us_rep,
            statement_frequency,
            minimum_balance_rule,
            customized_statement_print_steps,
            modified_at
        )
        VALUES (
            %(practice_id)s,
            %(clearinghouse_name)s,
            %(site_id)s,
            %(has_clearinghouse_login)s,
            %(eras_received_in_system)s,
            %(eras_not_received)s,
            %(paper_eobs_received)s,
            %(paper_eob_receive_method)s,
            %(attach_eobs_to_patient_accounts)s,
            %(dummy_patient_name)s,
            %(payment_posting_frequency)s,
            %(key_notes_for_us_rep)s,
            %(statement_frequency)s,
            %(minimum_balance_rule)s,
            %(customized_statement_print_steps)s,
            NOW()
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            clearinghouse_name = EXCLUDED.clearinghouse_name,
            site_id = EXCLUDED.site_id,
            has_clearinghouse_login = EXCLUDED.has_clearinghouse_login,
            eras_received_in_system = EXCLUDED.eras_received_in_system,
            eras_not_received = EXCLUDED.eras_not_received,
            paper_eobs_received = EXCLUDED.paper_eobs_received,
            paper_eob_receive_method = EXCLUDED.paper_eob_receive_method,
            attach_eobs_to_patient_accounts = EXCLUDED.attach_eobs_to_patient_accounts,
            dummy_patient_name = EXCLUDED.dummy_patient_name,
            payment_posting_frequency = EXCLUDED.payment_posting_frequency,
            key_notes_for_us_rep = EXCLUDED.key_notes_for_us_rep,
            statement_frequency = EXCLUDED.statement_frequency,
            minimum_balance_rule = EXCLUDED.minimum_balance_rule,
            customized_statement_print_steps = EXCLUDED.customized_statement_print_steps,
            modified_at = NOW()
    """, ch)

    # -------- COLLECTION AGENCY + INSURANCE LOGINS + MEETINGS SAVE --------

    cal = {
        "practice_id": practice_id,

        # booleans (store True/False in DB)
        "has_collection_agency": (request.form.get("has_collection_agency") == "Yes"),
        "has_insurance_login_access": (request.form.get("has_insurance_login_access") == "Yes"),

        # text fields (can be multiline if your column is TEXT)
        "collection_agency_name": clean(request.form.get("collection_agency_name")),
        "collection_agency_login_access": clean(request.form.get("collection_agency_login_access")),
        "insurance_with_login_access": clean(request.form.get("insurance_with_login_access")),
        "standard_monthly_reports": clean(request.form.get("standard_monthly_reports")),
        "custom_client_reports": clean(request.form.get("custom_client_reports")),

        # radios / selects (store as text)
        "required_meeting_participants": clean(request.form.get("required_meeting_participants")),
        "meeting_frequency": clean(request.form.get("meeting_frequency")),
        "meeting_mode": clean(request.form.get("meeting_mode")),

        "last_sent_to_client": clean(request.form.get("last_sent_to_client")),
        "last_response_received_from_client": clean(request.form.get("last_response_received_from_client")),
        "response_received_type": clean(request.form.get("response_received_type")),
    }

    cur.execute("""
        INSERT INTO collection_agency_and_insurance_logins (
            practice_id,
            has_collection_agency,
            collection_agency_name,
            collection_agency_login_access,
            insurance_with_login_access,
            has_insurance_login_access,
            standard_monthly_reports,
            custom_client_reports,
            required_meeting_participants,
            meeting_frequency,
            meeting_mode,
            last_sent_to_client,
            last_response_received_from_client,
            response_received_type, 
            modified_at
        )
        VALUES (
            %(practice_id)s,
            %(has_collection_agency)s,
            %(collection_agency_name)s,
            %(collection_agency_login_access)s,
            %(insurance_with_login_access)s,
            %(has_insurance_login_access)s,
            %(standard_monthly_reports)s,
            %(custom_client_reports)s,
            %(required_meeting_participants)s,
            %(meeting_frequency)s,
            %(meeting_mode)s,
            %(last_sent_to_client)s,
            %(last_response_received_from_client)s,
            %(response_received_type)s,
            NOW()
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            has_collection_agency = EXCLUDED.has_collection_agency,
            collection_agency_name = EXCLUDED.collection_agency_name,
            collection_agency_login_access = EXCLUDED.collection_agency_login_access,
            insurance_with_login_access = EXCLUDED.insurance_with_login_access,
            has_insurance_login_access = EXCLUDED.has_insurance_login_access,
            standard_monthly_reports = EXCLUDED.standard_monthly_reports,
            custom_client_reports = EXCLUDED.custom_client_reports,
            required_meeting_participants = EXCLUDED.required_meeting_participants,
            meeting_frequency = EXCLUDED.meeting_frequency,
            meeting_mode = EXCLUDED.meeting_mode,
            last_sent_to_client = EXCLUDED.last_sent_to_client,
            last_response_received_from_client = EXCLUDED.last_response_received_from_client,
            response_received_type = EXCLUDED.response_received_type,
            modified_at = NOW()
    """, cal)

    cur.execute("""
        INSERT INTO file_downloading_process (
            practice_id,
            office_superbill_scans,
            nursing_peritoneal_dialysis_superbills_scans,
            hospital_superbill_scans,
            dialysis_billing_scans,
            eob_scans,
            other_correspondence_scans,
            modified_at
        )
        VALUES (
            %(practice_id)s,
            %(office_superbill_scans)s,
            %(nursing_peritoneal_dialysis_superbills_scans)s,
            %(hospital_superbill_scans)s,
            %(dialysis_billing_scans)s,
            %(eob_scans)s,
            %(other_correspondence_scans)s,
            NOW()
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            office_superbill_scans = EXCLUDED.office_superbill_scans,
            nursing_peritoneal_dialysis_superbills_scans = EXCLUDED.nursing_peritoneal_dialysis_superbills_scans,
            hospital_superbill_scans = EXCLUDED.hospital_superbill_scans,
            dialysis_billing_scans = EXCLUDED.dialysis_billing_scans,
            eob_scans = EXCLUDED.eob_scans,
            other_correspondence_scans = EXCLUDED.other_correspondence_scans,
            modified_at = NOW()
    """, {
        "practice_id": practice_id,
        "office_superbill_scans": clean(data.get("office_superbill_scans")),
        "nursing_peritoneal_dialysis_superbills_scans": clean(data.get("nursing_peritoneal_dialysis_superbills_scans")),
        "hospital_superbill_scans": clean(data.get("hospital_superbill_scans")),
        "dialysis_billing_scans": clean(data.get("dialysis_billing_scans")),
        "eob_scans": clean(data.get("eob_scans")),
        "other_correspondence_scans": clean(data.get("other_correspondence_scans")),
    })

    cur.execute("""
        INSERT INTO demo_charge_entry_process (
            practice_id,
            scheduling,
            office_demographics,
            office_charges_entry,
            office_authorization,
            hospital_charges,
            dialysis_charge_entry_process,
            modified_at
        )
        VALUES (
            %(practice_id)s,
            %(scheduling)s,
            %(office_demographics)s,
            %(office_charges_entry)s,
            %(office_authorization)s,
            %(hospital_charges)s,
            %(dialysis_charge_entry_process)s,
            NOW()
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            scheduling = EXCLUDED.scheduling,
            office_demographics = EXCLUDED.office_demographics,
            office_charges_entry = EXCLUDED.office_charges_entry,
            office_authorization = EXCLUDED.office_authorization,
            hospital_charges = EXCLUDED.hospital_charges,
            dialysis_charge_entry_process = EXCLUDED.dialysis_charge_entry_process,
            modified_at = NOW()
    """, {
        "practice_id": practice_id,
        "scheduling": clean(data.get("scheduling")),
        "office_demographics": clean(data.get("office_demographics")),
        "office_charges_entry": clean(data.get("office_charges_entry")),
        "office_authorization": clean(data.get("office_authorization")),
        "hospital_charges": clean(data.get("hospital_charges")),
        "dialysis_charge_entry_process": clean(data.get("dialysis_charge_entry_process")),
    })

   

  # -------- CODING SAVE --------

    cur.execute("DELETE FROM coding WHERE practice_id = %s", (practice_id,))

    coding_rule = clean(data.get("coding_rule"))
    coding_cpt_rule = clean(data.get("coding_cpt_rule"))

    if coding_rule or coding_cpt_rule:
        cur.execute("""
            INSERT INTO coding (
                practice_id,
                facility_type,
                rule,
                cpt_rule,
                modified_at
            )
            VALUES (%s, %s, %s, %s, NOW())
        """, (
            practice_id,
            "general",
            coding_rule or "",
            coding_cpt_rule
        ))

    # -------- TOP DENIALS AND ACTION SAVE --------
    cur.execute("""
        INSERT INTO top_denials_and_actions (
            practice_id,
            auth,
            authorization_category,
            medical_record_request,
            medical_records_insufficient,
            overpayment_request,
            coverage_issue,
            coverage_issue_category,
            inconsistent_dx,
            hospice,
            primary_paid_more_than_sec_allowable,
            non_par_out_of_network,
            non_par_out_of_network_category,
            time_filing_limits,
            inclusive,
            modified_at
        )
        VALUES (
            %(practice_id)s,
            %(auth)s,
            %(authorization_category)s,
            %(medical_record_request)s,
            %(medical_records_insufficient)s,
            %(overpayment_request)s,
            %(coverage_issue)s,
            %(coverage_issue_category)s,
            %(inconsistent_dx)s,
            %(hospice)s,
            %(primary_paid_more_than_sec_allowable)s,
            %(non_par_out_of_network)s,
            %(non_par_out_of_network_category)s,
            %(time_filing_limits)s,
            %(inclusive)s,
            NOW()
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            auth = EXCLUDED.auth,
            authorization_category = EXCLUDED.authorization_category,
            medical_record_request = EXCLUDED.medical_record_request,
            medical_records_insufficient = EXCLUDED.medical_records_insufficient,
            overpayment_request = EXCLUDED.overpayment_request,
            coverage_issue = EXCLUDED.coverage_issue,
            coverage_issue_category = EXCLUDED.coverage_issue_category,
            inconsistent_dx = EXCLUDED.inconsistent_dx,
            hospice = EXCLUDED.hospice,
            primary_paid_more_than_sec_allowable = EXCLUDED.primary_paid_more_than_sec_allowable,
            non_par_out_of_network = EXCLUDED.non_par_out_of_network,
            non_par_out_of_network_category = EXCLUDED.non_par_out_of_network_category,
            time_filing_limits = EXCLUDED.time_filing_limits,
            inclusive = EXCLUDED.inclusive,
            modified_at = NOW()
    """, {
        "practice_id": practice_id,
        "auth": clean(data.get("auth")),
        "authorization_category": clean(data.get("authorization_category")),
        "medical_record_request": clean(data.get("medical_record_request")),
        "medical_records_insufficient": clean(data.get("medical_records_insufficient")),
        "overpayment_request": clean(data.get("overpayment_request")),
        "coverage_issue": clean(data.get("coverage_issue")),
        "coverage_issue_category": clean(data.get("coverage_issue_category")),
        "inconsistent_dx": clean(data.get("inconsistent_dx")),
        "hospice": clean(data.get("hospice")),
        "primary_paid_more_than_sec_allowable": clean(data.get("primary_paid_more_than_sec_allowable")),
        "non_par_out_of_network": clean(data.get("non_par_out_of_network")),
        "non_par_out_of_network_category": clean(data.get("non_par_out_of_network_category")),
        "time_filing_limits": clean(data.get("time_filing_limits")),
        "inclusive": clean(data.get("inclusive")),
    })

    # -------- PATIENT STATEMENT PROCESS SAVE --------
    psp = {
        "practice_id": practice_id,
        "generate_patient_balance_list": clean(request.form.get("generate_patient_balance_list")),
        "patient_statement_review_checklist": clean(request.form.get("patient_statement_review_checklist")),
    }

    cur.execute("""
        INSERT INTO patient_statement_process (
            practice_id,
            generate_patient_balance_list,
            patient_statement_review_checklist,
            modified_at
        )
        VALUES (
            %(practice_id)s,
            %(generate_patient_balance_list)s,
            %(patient_statement_review_checklist)s,
            NOW()
        )
        ON CONFLICT (practice_id)
        DO UPDATE SET
            generate_patient_balance_list = EXCLUDED.generate_patient_balance_list,
            patient_statement_review_checklist = EXCLUDED.patient_statement_review_checklist,
            modified_at = NOW()
    """, psp)

    # -------- SAVE GENERATE BALANCE BLOCK TEST --------
    save_field_block(
        cur,
        practice_id,
        "patient_statement_process",
        "generate_patient_balance_list",
        "generate_balance_block_type[]",
        "generate_balance_block_text[]",
        "generate_balance_block_image[]"
    )
    save_field_block(
        cur,
        practice_id,
        "patient_statement_process",
        "patient_statement_review_checklist",
        "review_checklist_block_type[]",
        "review_checklist_block_text[]",
        "review_checklist_block_image[]"
    )

    for section, field, prefix in BLOCK_FIELDS:
        save_field_block(
            cur,
            practice_id,
            section,
            field,
            f"{prefix}_block_type[]",
            f"{prefix}_block_text[]",
            f"{prefix}_block_image[]"
        )

   


    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("rulebook", practice_id=practice_id))



# ---------------- RULEBOOK BLOCK HELPERS ----------------
def read_field_blocks(cur, practice_id, section_key, field_key):
    cur.execute("""
        SELECT id, block_order, block_type, block_text
        FROM rulebook_field_blocks
        WHERE practice_id = %s
          AND section_key = %s
          AND field_key = %s
          AND COALESCE(isactive, true) = true
        ORDER BY block_order
    """, (practice_id, section_key, field_key))

    return [
        {
            "id": r[0],
            "block_order": r[1],
            "block_type": r[2],
            "block_text": r[3] or ""
        }
        for r in cur.fetchall()
    ]


def save_field_block(cur, practice_id, section_key, field_key, block_type_field, block_text_field, image_field):

    block_types = request.form.getlist(block_type_field)
    block_texts = request.form.getlist(block_text_field)
    block_images = request.files.getlist(image_field)

   
    total_blocks = max(len(block_types), len(block_texts))

    for i in range(total_blocks):

        block_type = (block_types[i] if i < len(block_types) else "paragraph").strip()
        block_text = (block_texts[i] if i < len(block_texts) else "").strip()

        if not block_text:
            continue

        # get next order
        cur.execute("""
            SELECT COALESCE(MAX(block_order), 0) + 1
            FROM rulebook_field_blocks
            WHERE practice_id = %s
              AND section_key = %s
              AND field_key = %s
        """, (practice_id, section_key, field_key))

        next_order = cur.fetchone()[0]

        # save block
        cur.execute("""
            INSERT INTO rulebook_field_blocks (
                practice_id,
                section_key,
                field_key,
                block_order,
                block_type,
                block_text,
                modified_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            practice_id,
            section_key,
            field_key,
            next_order,
            block_type,
            block_text
        ))

        # handle image
        if i < len(block_images):
            f = block_images[i]

            if f and f.filename:
                original = secure_filename(f.filename)
                ext = os.path.splitext(original)[1].lower()

                if ext in ALLOWED_EXT:

                    new_name = f"{uuid.uuid4().hex}{ext}"

                    folder = os.path.join(
                        UPLOAD_ROOT,
                        f"practice_{practice_id}",
                        section_key,
                        field_key
                    )
                    os.makedirs(folder, exist_ok=True)

                    filepath = os.path.join(folder, new_name)
                    f.save(filepath)

                    cur.execute("""
                        INSERT INTO practice_images (
                            practice_id,
                            section_key,
                            field_key,
                            block_order,
                            file_name,
                            original_name,
                            mime_type
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        practice_id,
                        section_key,
                        field_key,
                        next_order,
                        new_name,
                        original,
                        f.mimetype
                    ))
     


# ---------------- NPI VERIFICATION ----------------
@app.route("/rulebook/api/verify-npi/<npi_number>")
def verify_npi(npi_number):
    api_url = f"https://npiregistry.cms.hhs.gov/api/?version=2.1&number={npi_number}"

    try:
        r = requests.get(api_url, timeout=5)
        data = r.json()

        if data.get("result_count", 0) > 0:
            provider = data["results"][0]["basic"]
            name = provider.get("organization_name") or \
                   f"{provider.get('first_name','')} {provider.get('last_name','')}".strip()

            return jsonify({"status": "verified", "name": name})

        return jsonify({"status": "denied"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

 
  


UPLOAD_ROOT = os.path.join(app.root_path, "static", "uploads")

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}

def save_field_image(cur, practice_id: int, section_key: str, field_key: str):
    """
    expects <input type="file" name="img__SECTION__FIELD">
    """
    f = request.files.get(f"img__{section_key}__{field_key}")
    if not f or not f.filename:
        return

    original = secure_filename(f.filename)
    ext = os.path.splitext(original)[1].lower()
    if ext not in ALLOWED_EXT:
        return

    # unique file name
    new_name = f"{uuid.uuid4().hex}{ext}"

    folder = os.path.join(UPLOAD_ROOT, f"practice_{practice_id}", section_key, field_key)
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, new_name)
    f.save(filepath)

    # insert row
    cur.execute("""
        INSERT INTO practice_images (practice_id, section_key, field_key, file_name, original_name, mime_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (practice_id, section_key, field_key, new_name, original, f.mimetype))

    

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("HTTP_PLATFORM_PORT", 8000))
    app.run(host="127.0.0.1", port=port, debug=False)
