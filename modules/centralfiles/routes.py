from modules.centralfiles.classes import centralfiles, update_mind_class_estimation
from fastapi.responses import JSONResponse, HTMLResponse, Response
from library.authperms import set_permission, AuthPerms
from fastapi.templating import Jinja2Templates
from library.logbook import LogBookHandler
from library.auth import route_prechecks
from fastapi import APIRouter, Request
from library.email import client_email
from library.database import DB_PATH
from library.auth import authbook
from typing import Dict, Optional
from collections import Counter
from pydantic import BaseModel
import asyncio
import datetime
import sqlite3
import base64
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
logbook = LogBookHandler("Central Files")

class NamePostData(BaseModel):
    name: str

class LoginData(BaseModel):
    username: str

class ModifyFileData(BaseModel):
    cfid: int
    field: str
    value: str

class NoteData(BaseModel):
    note_id: int
    note: str

class NoteDeleteData(BaseModel):
    note_id: int

class NoteCreateData(BaseModel):
    cfid: int
    note: str

class DeleteNameData(BaseModel):
    cfid: int

# noinspection PyUnusedLocal
@router.get("/files", response_class=HTMLResponse)
@set_permission(permission="central_files")
async def show_reg(request: Request):
    token:str = route_prechecks(request)
    username = authbook.token_owner(token)
    logbook.info(f"IP {request.client.host}, User {username} has accessed the C/F Page.")
    is_admin = authbook.is_user_admin(username)
    return templates.TemplateResponse(request, "index.html", {'user': username, 'user_is_admin': is_admin})

@router.get("/files/dupecheck/{name}", response_class=HTMLResponse)
@set_permission(permission="central_files")
async def dupe_check(request: Request, name: str):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host}, User {authbook.token_owner(token)} Has checked for duplicates for cfid {name}")
    result = centralfiles.dupe_check(str(name))
    if result["exists"]:
        return JSONResponse(content={"exists": True, "cfids": result["cfids"]}, status_code=200)
    else:
        if result.get("error", None) is None:
            return JSONResponse(content={"exists": False}, status_code=404)
        else:
            return JSONResponse(content={"exists": -1, "error": result["error"]}, status_code=500)

@router.get("/files/get/{cfid}")
@set_permission(permission="central_files")
async def get_file(request: Request, cfid: int):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} Has fetched the folder for cfid {cfid} under account {authbook.token_owner(token)}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    assosciated_invoices = centralfiles.get_assosciated_invoices(cfid)
    assosciated_debts = centralfiles.get_assosciated_debts(cfid)
    dianetics_profile = centralfiles.dianetics.get_profile(cfid=cfid)

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "profile": profile,
            "invoices": assosciated_invoices,
            "debts": assosciated_debts,
            "dianetics": dianetics_profile
        }
    )

@router.post("/api/files/modify", response_class=JSONResponse)
@set_permission(permission="central_files")
async def modify_file(request: Request, data: ModifyFileData):
    token:str = route_prechecks(request)
    user = authbook.token_owner(token)
    logbook.info(f"Request from {request.client.host} ({user}) to modify cfid {data.cfid}: field '{data.field}' with value '{data.value}'")
    is_staff = centralfiles.get_profile_is_staff(data.cfid)

    dn_fields = [
        'is_dianetics',
        'last_action',
        'sonic_shutoff',
        'visio_shutoff',
        'stuck_case',
        'stuck_age',
        'control_case',
        'fabricator_case',
        'tone_level',
        'can_handle_life',
        'chem_assist'
    ]

    try:
        if data.field == "age":
            centralfiles.modify(data.cfid).age(int(data.value))
            success = True
        elif data.field == "dob":
            if data.value.count("-") == 0:
                return JSONResponse(content={"success": False, "error": "Invalid time format"}, status_code=400)

            datetime_obj = datetime.datetime.now().strptime(data.value.lower(), "%Y-%m-%d")
            centralfiles.modify(data.cfid).date_of_birth(
                date_of_birth=datetime_obj
            )
            success = True
        elif data.field == "occupation":
            if is_staff:
                return JSONResponse(content={"success": False, "error": "You cannot modify a staff members occupation using CF."}, status_code=400)
            centralfiles.modify(data.cfid).occupation(data.value)
            success = True
        elif data.field == "pronouns":
            if not len(data.value.split("/")) == 2:
                return JSONResponse(content={"success": False, "error": "Format for pronouns is Invalid. Enter pronouns like She/Her or They/Him"}, status_code=400)
            centralfiles.modify(data.cfid).pronouns(
                subjective=data.value.split("/")[0],
                objective=data.value.split("/")[1],
            )
            success = True
        elif data.field == "name":
            centralfiles.modify(data.cfid).name(data.value)
            success = True
        elif data.field == "first_name":
            centralfiles.modify(data.cfid).first_name(data.value)
            success = True
        elif data.field == "middle_name":
            centralfiles.modify(data.cfid).middle_name(data.value)
            success = True
        elif data.field == "last_name":
            centralfiles.modify(data.cfid).last_name(data.value)
            success = True
        elif data.field == "phone_no":
            centralfiles.modify(data.cfid).phone_no(data.value)
            success = True
        elif data.field == "email_addr":
            centralfiles.modify(data.cfid).email_address(data.value)
            success = True
        elif data.field == "home_addr":
            centralfiles.modify(data.cfid).home_address(data.value)
            success = True
        elif data.field == "prof_type":
            centralfiles.modify(data.cfid).profile_type(data.value)
            success = True
        else:
            if data.field not in dn_fields:
                raise ValueError(f"Invalid field specified, {data.field}")

        # Permission protected fields.
        if data.field in dn_fields:
            if AuthPerms.check_allowed(user, "dianetics") is False:
                logbook.warning(f"User {user} attempted to modify Dianetics field '{data.field}' without permission.")
                return JSONResponse(content={"success": False, "error": "Insufficient permissions to modify Dianetics fields."}, status_code=403)

            if data.field == "is_dianetics":
                centralfiles.modify(data.cfid).is_dn_pc(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "last_action":
                centralfiles.dianetics.modify(data.cfid).add_action(data.value)
                success = True
            elif data.field == "sonic_shutoff":
                centralfiles.dianetics.modify(data.cfid).is_sonic_off(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "visio_shutoff":
                centralfiles.dianetics.modify(data.cfid).is_visio_off(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "stuck_case":
                centralfiles.dianetics.modify(data.cfid).is_stuck_case(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "stuck_age":
                centralfiles.dianetics.modify(data.cfid).stuck_age(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "control_case":
                centralfiles.dianetics.modify(data.cfid).is_control_case(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "fabricator_case":
                centralfiles.dianetics.modify(data.cfid).is_fabricator_case(True if data.value.lower() == "true" else False)
                success = True
            elif data.field == "tone_level":
                centralfiles.dianetics.tonescale(data.cfid).set_level(float(data.value))
                success = True
            elif data.field == "can_handle_life":
                centralfiles.modify(data.cfid).can_handle_life(data.value)
                success = True
            elif data.field == "chem_assist":
                centralfiles.modify(data.cfid).chem_assist(data.value)
                success = True
            else:
                success = False

            if data.field in ['can_handle_life', 'visio_shutoff', 'sonic_shutoff']:
                # Update mind class estimation if these fields are changed
                update_mind_class_estimation(str(data.cfid))

        if success:
            return JSONResponse(content={"success": True}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "error": "Update failed"}, status_code=400)
    except Exception as err:
        logbook.error(f"Error updating cfid {data.cfid}: {err}", exception=err)
        return JSONResponse(content={"success": False, "error": "Internal server error"}, status_code=500)

@router.post("/api/files/note/modify", response_class=JSONResponse)
@set_permission(permission="central_files")
async def modify_note(request: Request, data: NoteData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host} under account {authbook.token_owner(token)} to modify note ID {data.note_id} to \"{data.note}\"")
    success = centralfiles.notes(data.note_id).modify(data.note)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Update failed"}, status_code=400)

@router.post("/api/files/note/delete", response_class=JSONResponse)
@set_permission(permission="central_files")
async def delete_note(request: Request, data: NoteDeleteData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host} to DELETE note ID {data.note_id} by account {authbook.token_owner(token)}")
    success = centralfiles.notes(data.note_id).delete()
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Deletion failed"}, status_code=400)

@router.post("/api/files/note/create", response_class=JSONResponse)
@set_permission(permission="central_files")
async def create_note(request: Request, data: NoteCreateData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host} to CREATE a note by account {authbook.token_owner(token)}")

    author = authbook.token_owner(token)
    note_id = centralfiles.notes.create(data.cfid, data.note, author)
    success = note_id is not None

    if success:
        return JSONResponse(content={
            "success": True,
            "note_id": note_id,
            "add_date": datetime.datetime.now(datetime.UTC).strftime("%m/%d/%Y %H:%M:%S"),
            "author": author
            },
            status_code=200
        )
    else:
        return JSONResponse(content={"success": False, "error": "Create failed"}, status_code=400)

@router.get("/api/files/get_names", response_class=HTMLResponse)
@set_permission(permission="central_files")
async def get_names(request: Request):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} Has fetched all names under account {authbook.token_owner(token)}")
    names, cfid_list = centralfiles.get_names()
    data = {
        "names": names,
        "cfids": cfid_list
    }
    return JSONResponse(
        content=data,
        status_code=200,
    )

@router.get("/api/files/get_all_profile", response_class=HTMLResponse)
@set_permission(permission="central_files")
async def get_all_profiles(request: Request):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} Has fetched all names under account {authbook.token_owner(token)}")
    data = {
        "profiles": centralfiles.get_all_profiles(),
    }
    return JSONResponse(
        content=data,
        status_code=200,
    )

@router.post("/api/files/get_profile", response_class=JSONResponse)
@set_permission(permission="central_files")
async def get_profile(request: Request, data: NamePostData):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} fetched profile '{data.name}' under account {authbook.token_owner(token)}")
    try:
        profile = centralfiles.get_profile(name=data.name)
        return JSONResponse(content=profile, status_code=200)
    except centralfiles.errors.ProfileNotFound:
        return JSONResponse(content={"error": "Profile not found."}, status_code=404)
    except centralfiles.errors.TooManyProfiles:
        return JSONResponse(content={"error": "Multiple profiles with that name."}, status_code=400)

class CreateNamePostData(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    alias: Optional[str] = None
    profile_type: str

@router.post("/api/files/create", response_class=JSONResponse)
@set_permission(permission="central_files")
async def create_name(request: Request, data: CreateNamePostData):
    token:str = route_prechecks(request)
    owner = authbook.token_owner(token)
    logbook.info(f"Request from IP {request.client.host}; Request from account {owner} to CREATE name '{data.first_name}', alias {data.alias}")

    if not data.alias:
        cfid = centralfiles.add_name(
            first_name=data.first_name,
            middle_name=data.middle_name,
            last_name=data.last_name,
            profile_type=data.profile_type
        )
    else:
        cfid = centralfiles.add_name(
            alias=data.alias,
            profile_type=data.profile_type
        )

    if cfid is not None:
        return JSONResponse(content={"success": True, "cfid": cfid}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Creation failed"}, status_code=400)

@router.post("/api/files/delete", response_class=JSONResponse)
@set_permission(permission="central_files")
async def delete_name(request: Request, data: DeleteNameData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to DELETE CFID '{data.cfid}'")
    success = centralfiles.delete_name(data.cfid)
    if success is True:
        return JSONResponse(content={"success": True}, status_code=200)
    elif success == -1:  # Staff account
        return JSONResponse(
            content={
                "success": False,
                "error": "This is a staff account, and can only be deleted through the staff management portal."
            },
            status_code=401
        )
    else:
        return JSONResponse(content={"success": False, "error": "Deletion failed"}, status_code=400)

class SubmitActionData(BaseModel):
    cfid: int
    action: str

@router.post("/api/files/submit_action", response_class=JSONResponse)
@set_permission(["central_files", "dianetics"])
async def submit_action(request: Request, data: SubmitActionData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to SUBMIT action '{data.action}' for cfid {data.cfid}")
    success = centralfiles.dianetics.modify(data.cfid).add_action(data.action)
    if success:
        return JSONResponse(content={"success": True}, status_code=200)
    else:
        return JSONResponse(content={"success": False, "error": "Action submission failed"}, status_code=400)

@router.get("/api/files/get_actions/{cfid}", response_class=JSONResponse)
@set_permission(["central_files", "dianetics"])
async def submit_action(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; Request from account {authbook.token_owner(token)} to get all auditing actions for cfid {cfid}")
    actions = centralfiles.dianetics.list_actions(cfid)
    return JSONResponse(content=actions, status_code=200)

@router.get("/api/files/{cfid}/profile_icon")
@set_permission(permission="central_files")
async def get_profile_image(request: Request, cfid: int):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to get profile image for cfid {cfid}")
    image_data = centralfiles.get_profile_image(cfid)
    
    # Return the image bytes with appropriate headers
    return Response(
        content=image_data,
        media_type="image/jpeg"  # or "image/png", "image/gif" depending on your image format
    )

# Simple in-memory cache with TTL
class ProfileCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self.cache: Dict[int, Dict] = {}
        self.timestamps: Dict[int, float] = {}
        self.ttl = ttl_seconds
        self.lock = asyncio.Lock()
    
    async def get(self, cfid: int) -> Optional[Dict]:
        async with self.lock:
            if cfid in self.cache:
                # Check if cache entry is still valid
                if asyncio.get_event_loop().time() - self.timestamps[cfid] < self.ttl:
                    return self.cache[cfid]
                else:
                    # Remove expired entry
                    del self.cache[cfid]
                    del self.timestamps[cfid]
            return None
    
    async def set(self, cfid: int, profile: Dict):
        async with self.lock:
            self.cache[cfid] = profile
            self.timestamps[cfid] = asyncio.get_event_loop().time()
    
    async def invalidate(self, cfid: int):
        async with self.lock:
            if cfid in self.cache:
                del self.cache[cfid]
                del self.timestamps[cfid]

# Initialize cache
profile_cache = ProfileCache(ttl_seconds=30)

async def get_cached_profile(cfid: int) -> Optional[Dict]:
    """Get profile from cache or database with caching"""
    # Try cache first
    cached_profile = await profile_cache.get(cfid)
    if cached_profile:
        logbook.info(f"Cache hit for profile cfid {cfid}")
        return cached_profile
    
    # Cache miss, fetch from database
    profile = centralfiles.get_profile(cfid=cfid)
    if profile:
        await profile_cache.set(cfid, profile)
    
    return profile

# Helper function for common response logic
async def get_profile_field(cfid: int, field_name: str, field_display_name: str, request: Request, token: str):
    """Helper to get a specific field from profile with caching"""
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to get profile {field_display_name} for cfid {cfid}")
    
    profile = await get_cached_profile(cfid)
    if not profile:
        return HTMLResponse(content="Profile Not Found", status_code=404)
    
    field_value = profile.get(field_name)
    if field_value is None:
        return HTMLResponse(content=f"{field_display_name.capitalize()} Not Available", status_code=404)
    
    return HTMLResponse(content=field_value, status_code=200)

# Used by invoicing
@router.get("/api/files/{cfid}/name")
@set_permission(permission="central_files")
async def get_profile_name(request: Request, cfid: int):
    token:str = route_prechecks(request)
    return await get_profile_field(cfid, 'name', 'name', request, token)

# Used by invoicing
@router.get("/api/files/{cfid}/address")
@set_permission(permission="central_files")
async def get_profile_address(request: Request, cfid: int):
    token:str = route_prechecks(request)
    return await get_profile_field(cfid, 'home_addr', 'address', request, token)

@router.get("/api/files/{cfid}/email")
@set_permission(permission="central_files")
async def get_profile_email(request: Request, cfid: int):
    token:str = route_prechecks(request)
    return await get_profile_field(cfid, 'email_addr', 'email', request, token)

@router.get("/api/files/{cfid}/phone")
@set_permission(permission="central_files")
async def get_profile_phone(request: Request, cfid: int):
    token:str = route_prechecks(request)
    return await get_profile_field(cfid, 'phone_no', 'phone number', request, token)

@router.get("/api/files/{cfid}/is_staff")
@set_permission(permission="central_files")
async def get_profile_is_staff(request: Request, cfid: int):
    route_prechecks(request)
    return {
        "is_staff": centralfiles.get_profile_is_staff(cfid)
    }

class UploadProfileImageData(BaseModel):
    cfid: int
    img_bytes: bytes

@router.post("/api/files/upload_profile_picture", response_class=JSONResponse)
@set_permission(permission="central_files")
async def upload_profile_image(request: Request, data: UploadProfileImageData):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to upload profile image for cfid {data.cfid}")
    
    try:
        # Decode base64 string back to bytes
        file_bytes = base64.b64decode(data.img_bytes)
        
        success = centralfiles.modify(data.cfid).profile_image(file_bytes)
        if success:
            return JSONResponse(content={"success": True}, status_code=200)
        else:
            return JSONResponse(content={"success": False, "error": "Upload failed"}, status_code=400)

    except base64.binascii.Error as e:
        logbook.error(f"Base64 decoding error for cfid {data.cfid}: {e}")
        return JSONResponse(content={"success": False, "error": "Invalid image data format"}, status_code=400)
    except Exception as e:
        logbook.error(f"Unexpected error uploading profile image for cfid {data.cfid}: {e}")
        return JSONResponse(content={"success": False, "error": "Internal server error"}, status_code=500)

@router.get("/api/files/{cfid}/occupation")
@set_permission(permission="central_files")
async def get_occupation(request: Request, cfid: int):
    token:str = route_prechecks(request)
    logbook.info(f"Request from IP {request.client.host}; account {authbook.token_owner(token)} to get the occupation for cfid {cfid}")
    try:
        occupation_data = centralfiles.get_occupation(cfid)
    except centralfiles.errors.ProfileNotFound:
        return JSONResponse(content={"error": "Profile not found."}, status_code=404)
    return HTMLResponse(occupation_data, status_code=200)

# A Webpage for full PC Management
@router.get("/files/get/{cfid}/auditing")
@set_permission(["central_files", "dianetics"])
async def load_pc_file(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed the PC folder of {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    dianetics_profile = centralfiles.dianetics.get_profile(cfid=cfid)
    return templates.TemplateResponse(
        request,
        "pc_profile.html",
        {
            "profile": profile,
            "dianetics": dianetics_profile
        }
    )

class SetThetaData(BaseModel):
    cfid: int
    theta_count: int

@router.post("/api/files/set_theta")
@set_permission(["central_files", "dianetics"])
async def set_theta(request: Request, post_data: SetThetaData):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting CFID {post_data.cfid}'s Theta Count to {post_data.theta_count}")
    success = centralfiles.dianetics.modify(post_data.cfid).set_theta_count(post_data.theta_count)
    update_mind_class_estimation(str(post_data.cfid))

    return JSONResponse(
        content={"success": success},
        status_code=200 if success else 500
    )

@router.get("/files/get/{cfid}/agreements")
@set_permission(permission="central_files")
async def load_agreements_page(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed the PC folder of {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        request,
        "agreements.html",
        {
            "profile": profile,
        }
    )

class add_agreement_data(BaseModel):
    agreement: str
    date_promised: str

@router.post("/api/files/{cfid}/agreements/add")
@set_permission(permission="central_files")
async def route_add_agreement(request: Request, data:add_agreement_data, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has added an agreement for CFID {cfid}, that agreement being \"{data.agreement}\"")
    
    try:
        data.date_promised = datetime.datetime.strptime(data.date_promised, "%Y-%m-%d")
    except ValueError as err:
        return JSONResponse(
            content={
                "error": str(err)
            },
            status_code=400
        )

    success = centralfiles.agreements.add_agreement(
        cfid=cfid,
        agreement=data.agreement,
        date_agreed=data.date_promised
    )

    return JSONResponse(
        content={
            "success": success
        },
        status_code=200
    )

@router.get('/api/files/{cfid}/agreements/get')
@set_permission(permission="central_files")
async def route_get_agreements(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is listing all agreements with CFID {cfid}.")

    agreements_list:list = centralfiles.agreements.get_agreements(cfid=cfid)

    if agreements_list is False:
        return JSONResponse(
            content={'error': "Couldn't get the list of agreements."},
            status_code=400
        )

    return JSONResponse(
        content=agreements_list,
        status_code=200
    )

class SetFulfilledData(BaseModel):
    agreement_id: int
    value: bool

@router.post('/api/files/{cfid}/agreements/set')
@set_permission(permission="central_files")
async def route_set_fulfilled_status(request: Request, data: SetFulfilledData, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is listing all agreements with CFID {cfid}.")

    success = centralfiles.agreements.set_fulfilled_status(cfid=int(cfid), agreement_id=int(data.agreement_id), value=bool(data.value))

    return HTMLResponse(
        content=str(success),
        status_code=200
    )

class DelAgreementData(BaseModel):
    agreement_id: int

@router.post('/api/files/{cfid}/agreements/delete')
@set_permission(permission="central_files")
async def route_set_fulfilled_status(request: Request, data: DelAgreementData, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is listing all agreements with CFID {cfid}.")

    success = centralfiles.agreements.delete(cfid=cfid, agreement_id=int(data.agreement_id))

    return HTMLResponse(
        content=str(success),
        status_code=200
    )
 
class AuditingLog:
    def list_all_sessions(cfid):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    SELECT session_id, date, summary, duration, status_code FROM sessions_list WHERE preclear_cfid = ?
                    """,
                    (cfid,)
                )
                data = cur.fetchall()
            except sqlite3.OperationalError as err:
                logbook.error(f"Error while fetching all session actions for CFID {cfid}", exception=err)
                return False
            
        parsed_data = []
        for row in data:
            parsed_data.append({
                "session_id": row[0],
                "date": row[1],
                "summary": str(row[2]),
                "duration": int(row[3]),
                "status_code": int(row[4]),
            })
        return parsed_data

    def new_session(date:datetime.datetime, cfid:int, auditor:str):
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO sessions_list (date, summary, duration, auditor, preclear_cfid, status_code)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (date, "Enter a summary!", 0, auditor, cfid, 2)
                )
                conn.commit()
                session_id = cur.lastrowid
            except sqlite3.OperationalError as err:
                logbook.error(f"Error while fetching all session actions for CFID {cfid}", exception=err)
                return False

        return session_id

    class session:
        def __init__(self, session_id):
            self.session_id = int(session_id)
            self.data = self.get_session_details()
            if self.data is False:
                raise LookupError("Could not find session")  # Session non-existent.

        def set_status(self, value:int=1):
            # Stat 1 = Comp'd, Stat 2 = Pending, Stat 3 = Cancelled
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE sessions_list
                        SET status_code = ? WHERE session_id = ?
                        """,
                        (value, self.session_id)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't mark session as code {value}!", exception=err)
                    return False
            return True

        def delete_action(self, action_id:int):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        DELETE FROM session_actions WHERE action_id = ?
                        """,
                        (int(action_id),)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't delete an action from the DB: {err}", exception=err)
                    return False
            return True

        def set_action_status(self, status, action_id):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE session_actions
                        SET completed = ? WHERE action_id = ?
                        """,
                        (bool(status), int(action_id))
                    )
                    conn.commit()
                    return cur.lastrowid
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't set an action's status for the DB: {err}", exception=err)
                    return False

        def add_action(self, action_text):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        INSERT INTO session_actions (session_id, action, completed)
                        VALUES (?, ?, ?)
                        """,
                        (self.session_id, action_text, False)
                    )
                    conn.commit()
                    return cur.lastrowid
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't add an action to the DB: {err}", exception=err)
                    return False

        def delete_engram(self, engram_id):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        DELETE FROM session_engrams WHERE session_id = ? AND engram_id = ?
                        """,
                        (self.session_id, engram_id,)
                    )
                    return True
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't delete an engram from the DB: {err}", exception=err)
                    return False

        def list_engrams(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT engram_id, actions, incident, somatic, incident_age FROM session_engrams WHERE session_id = ?
                        """,
                        (self.session_id,)
                    )
                    data = cur.fetchall()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't add an engram to the DB: {err}", exception=err)
                    return False
            
            parsed_data = []
            for engram in data:
                parsed_data.append({
                    "engram_id": engram[0],
                    "actions": engram[1],
                    "incident": engram[2],
                    "somatic": engram[3],
                    "incident_age": engram[4],
                })
            return parsed_data

        def get_session_details(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT session_id, preclear_cfid, date, summary, duration, auditor, remarks, status_code FROM sessions_list WHERE session_id = ?
                        """,
                        (self.session_id,)
                    )
                    data = cur.fetchone()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error while fetching all session actions for session ID {self.session_id}", exception=err)
                    return False
                
            if not data:
                return False
            
            return {
                "session_id": data[0],
                "preclear_cfid": data[1],
                "date": data[2],
                "summary": data[3],
                "duration": data[4],
                "auditor": data[5],
                "remarks": data[6],
                "status_code": data[7]
            }

        def list_planned_actions(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        SELECT action_id, action, completed FROM session_actions WHERE session_id = ?
                        """,
                        (self.session_id,)
                    )
                    data = cur.fetchall()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Error while fetching all session actions for session ID {self.session_id}", exception=err)
                    return False

            parsed_data = []
            for row in data:
                parsed_data.append({
                    "session_id": self.session_id,
                    "action_id": row[0],
                    "action_text": row[1],
                    "completed": bool(row[2])
                })
            return parsed_data

        def add_engram(self, actions:str, incident:str, somatic:str, incident_age:int):
            session_id = self.session_id
            actions = str(actions)
            incident = str(incident)
            somatic = str(somatic)
            incident_age = int(incident_age)
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        INSERT INTO session_engrams (session_id, actions, incident, somatic, incident_age)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (session_id, actions, incident, somatic, incident_age)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Couldn't add an engram to the DB: {err}", exception=err)
                    return False
            return True

        def set_remarks_value(self, text_value:str):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE sessions_list
                        SET remarks = ?
                        WHERE session_id = ?
                        """,
                        (text_value, self.session_id,)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Failed to update the session's saved remarks: {err}", exception=err)
                    return False
            return True

        def set_session_details(self, preclear_cfid, date, summary, duration, auditor):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        UPDATE sessions_list
                        SET date = ?, summary = ?, duration = ?, auditor = ?
                        WHERE session_id = ? AND preclear_cfid = ?
                        """,
                        (date, summary, duration, auditor, self.session_id, preclear_cfid)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Failed to set session details for the session: {err}", exception=err)
                    return False
            return True
        
        def delete_session(self):
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        """
                        DELETE FROM sessions_list WHERE session_id = ?
                        """,
                        (self.session_id,)
                    )
                    conn.commit()
                except sqlite3.OperationalError as err:
                    logbook.error(f"Failed to delete the session {self.session_id}: {err}", exception=err)
                    return False
            return True

@router.get("/files/get/{cfid}/sessions")
@set_permission(["central_files", "dianetics"])
async def load_sessions_page(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed the session records of {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        request,
        "sessions_list.html",
        {
            "profile": profile,
        }
    )

@router.get("/api/files/get/{cfid}/sessions/list_all")
@set_permission(["central_files", "dianetics"])
async def list_all_sessions(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed the session records of {cfid}")
    
    all_sessions = AuditingLog.list_all_sessions(cfid)

    return JSONResponse(
        content=all_sessions,
        status_code=200
    )

@router.get("/api/files/get/{cfid}/sessions/create/{date}")
@set_permission(["central_files", "dianetics"])
async def create_session(request: Request, cfid:int, date:str):
    token:str = route_prechecks(request)
    username = authbook.token_owner(token)
    logbook.info(f"{request.client.host} ({username}) Has accessed the session records of {cfid}")
    
    try:
        cfid = int(cfid)
    except ValueError:
        return HTMLResponse(
            content={
                "error": "Incorrect cfid type. Expected INT"
            },
            status_code=400
        )
    try:
        date = datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return HTMLResponse(
            content={
                "error": "Incorrect date format. Expected str -> YYYY/MM/DD"
            },
            status_code=400
        )

    new_session_id = AuditingLog.new_session(
        date=date,
        cfid=cfid,
        auditor=username
    )

    return HTMLResponse(
        content=str(new_session_id),
        status_code=200
    )

@router.get("/files/get/{cfid}/sessions/{session_id}")
@set_permission(["central_files", "dianetics"])
async def load_sessions_page(request: Request, cfid, session_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Has accessed to access the specific session {session_id} for {cfid}")
    
    try:
        session = AuditingLog.session(session_id=session_id)
    except LookupError:
        with open("modules/404.html", "r") as file:
            content = file.read()
        return HTMLResponse(content, status_code=404)

    profile = centralfiles.get_profile(cfid=int(cfid))
    session_data = session.get_session_details()

    status_map = {
        1: "completed",
        2: "scheduled",
        3: "cancelled"
    }
    text_status_code = status_map[session_data['status_code']]

    return templates.TemplateResponse(
        request,
        "session.html",
        context={
            "session": session_data,
            "profile": profile,
            "text_status_code": text_status_code
        }
    )

class set_details_data(BaseModel):
    date: str
    duration: int
    auditor: str
    summary: str

@router.post("/files/get/{cfid}/sessions/{session_id}/set_details")
@set_permission(["central_files", "dianetics"])
async def route_set_session_details(request: Request, cfid, session_id, data: set_details_data):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting details for the session {session_id} for CFID {cfid}")
    
    success = AuditingLog.session(session_id).set_session_details(
        preclear_cfid=cfid,
        date=data.date,
        summary=data.summary,
        duration=data.duration,
        auditor=data.auditor
    )

    return JSONResponse(
        content={
            "success": success,
        },
        status_code=200 if success else 500
    )

class set_remarks_data(BaseModel):
    text_value: str

@router.post("/api/files/get/{cfid}/sessions/{session_id}/set_remarks")
@set_permission(["central_files", "dianetics"])
async def route_set_session_details(request: Request, cfid, session_id, data: set_remarks_data):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting details for the session {session_id} for CFID {cfid}")

    success = AuditingLog.session(session_id).set_remarks_value(session_id, data.text_value)

    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

class AddEngramData(BaseModel):
    actions: str
    incident: str
    somatic: str
    incident_age: int

@router.post("/api/files/get/{cfid}/sessions/{session_id}/add_engram")
@set_permission(["central_files", "dianetics"])
async def route_add_engram(request: Request, cfid, session_id, data: AddEngramData):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting details for the session {session_id} for CFID {cfid}")

    success = AuditingLog.session(session_id).add_engram(data.actions, data.incident, data.somatic, data.incident_age)

    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

@router.get("/api/files/get/{cfid}/sessions/{session_id}/list_engrams")
@set_permission(["central_files", "dianetics"])
async def route_list_engrams(request: Request, cfid, session_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is setting details for the session {session_id} for CFID {cfid}")

    engrams = AuditingLog.session(session_id).list_engrams()

    return JSONResponse(
        content={
            "success": True,
            "engrams": engrams
        },
        status_code=200
    )

@router.delete("/api/files/get/{cfid}/sessions/{session_id}/delete_engram/{engram_id}")
@set_permission(["central_files", "dianetics"])
async def route_delete_engram(request: Request, cfid, session_id, engram_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is attempting to delete engram {engram_id} for session {session_id}, CFID {cfid}")
    success = AuditingLog.session(session_id=session_id).delete_engram(engram_id)
    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

@router.delete("/api/files/get/{cfid}/delete/session/{session_id}")
@set_permission(["central_files", "dianetics"])
async def delete_session(request: Request, cfid, session_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is attempting to delete the session {session_id} for {cfid}")
    success = AuditingLog.session(session_id).delete_session()
    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

@router.put("/api/files/get/{cfid}/session/set_status/{session_id}/{status_code}")
@set_permission(["central_files", "dianetics"])
async def session_set_status(request: Request, cfid, session_id:int, status_code:int):
    token:str = route_prechecks(request)
    valid_statuses = [
        1,  # Completed
        2,  # Pending
        3  # Cancelled
    ]
    if status_code not in valid_statuses:
        return JSONResponse(
            content={
                "success": False,
                "error": "Invalid status code, must be 1 (done), 2 (pending) or 3 (cancelled).",
            },
            status_code=400
        )

    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is attempting to mark session ID {session_id} as code {status_code} for {cfid}")
    success = AuditingLog.session(session_id).set_status(status_code)
    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 500
    )

@router.get("/api/files/get/{cfid}/sessions/{session_id}/list_actions")
@set_permission(["central_files", "dianetics"])
async def list_session_actions(request: Request, cfid, session_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) is listing planned actions for session {session_id} (CFID {cfid})")
    
    actions_list = AuditingLog.session(session_id).list_planned_actions()
    
    if actions_list is False:
        return JSONResponse(
            content={"success": False, "error": "Database query failed"},
            status_code=500
        )

    return JSONResponse(
        content={
            "success": True,
            "actions": actions_list
        },
        status_code=200
    )

class AddActionData(BaseModel):
    action_text: str

@router.post("/api/files/get/{cfid}/sessions/{session_id}/add_action")
@set_permission(["central_files", "dianetics"])
async def add_session_action(request: Request, cfid, session_id, data: AddActionData):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is adding an action for session {session_id}, CFID {cfid}")
    
    action_id = AuditingLog.session(session_id=session_id).add_action(data.action_text)

    return JSONResponse(
        content={
            "action_id": action_id
        },
        status_code=200
    )

class CompletedActionData(BaseModel):
    completed: bool

@router.post("/api/files/get/{cfid}/sessions/{session_id}/update_action/{action_id}")
@set_permission(["central_files", "dianetics"])
async def update_session_action(request: Request, cfid, session_id, action_id, data: CompletedActionData):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is adding an action for session {session_id}, CFID {cfid}")
    
    action_id = AuditingLog.session(session_id=session_id).set_action_status(data.completed, action_id=action_id)

    return JSONResponse(
        content={
            "action_id": action_id
        },
        status_code=200
    )

@router.delete("/api/files/get/{cfid}/sessions/{session_id}/delete_action/{action_id}")
@set_permission(["central_files", "dianetics"])
async def delete_session_action(request: Request, cfid, session_id, action_id):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is adding an action for session {session_id}, CFID {cfid}")
    
    session_id = int(session_id)
    cfid = int(cfid)
    action_id = int(action_id)

    success = AuditingLog.session(session_id).delete_action(action_id)

    return JSONResponse(
        content={
            "success": success
        },
        status_code=200 if success else 400
    )

@router.get("/files/get/{cfid}/scheduling")
@set_permission(["central_files", "dianetics"])
async def open_scheduling_page(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is accessing the scheduling page for {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        request,
        "scheduling.html",
        context={
            "profile": profile
        }
    )

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_week_dates(reference_date=None):
    """
    Given reference_date, return list of 7 date objects (Mon-Sun) for the week containing the reference_date.
    """
    if reference_date is None:
        ref = datetime.datetime.now().date()
    elif isinstance(reference_date, datetime.datetime):
        ref = reference_date.date()
    elif isinstance(reference_date, str):
        ref = datetime.datetime.strptime(reference_date, "%Y-%m-%d").date()
    else:
        ref = reference_date

    # Calculate Monday of the week containing the reference date
    # weekday(): Monday=0, Sunday=6
    offset = ref.weekday()  # 0-6
    monday = ref - datetime.timedelta(days=offset)

    return [monday + datetime.timedelta(days=i) for i in range(7)]

def get_scheduling_data(cfid, reference_date=None):
    """
    Returns FULL WEEK (Monday\u2013Sunday) structured schedule data.
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # --- Get full week range ---
        week_dates = get_week_dates(reference_date)
        date_strings = [d.isoformat() for d in week_dates]

        # ------------------------------------------------------------------------------
        # 1. Fetch normal (non-repeating) schedules
        # ------------------------------------------------------------------------------
        cur.execute(
            f"""
            SELECT cfid, date, time_str, activity, auditor, room
            FROM dn_schedule_data
            WHERE cfid = ?
            AND DATE(date) IN ({','.join('?' * len(date_strings))})
            """,
            (cfid, *date_strings)
        )
        normal_schedules = cur.fetchall()

        # ------------------------------------------------------------------------------
        # 2. Fetch repeating schedules
        # ------------------------------------------------------------------------------
        cur.execute(
            """
            SELECT cfid, start_date, repeat_integer, end_date,
                   time_str, activity, auditor, room
            FROM dn_scheduling_data_repeating
            WHERE cfid = ?
            """,
            (cfid,)
        )
        repeating_schedules = cur.fetchall()

    # ------------------------------------------------------------------------------
    # Build frontend-ready result: every day present
    # ------------------------------------------------------------------------------
    output = { day: {} for day in DAY_NAMES }

    # Map ISO-date to weekday name
    date_to_day_name = { date_strings[i]: DAY_NAMES[i] for i in range(7) }

    # Helper to insert
    def insert(day_name, time_str, activity, auditor, room):
        output[day_name][time_str] = {
            "time": time_str,
            "activity": activity,
            "auditor": auditor,
            "room": room
        }

    # ------------------------------------------------------------------------------
    # Insert NORMAL schedules
    # ------------------------------------------------------------------------------
    for row in normal_schedules:
        date = row["date"].split(" ")[0]  # Cuts out all after the date
        day_name = date_to_day_name[date]
        insert(day_name, row["time_str"], row["activity"], row["auditor"], row["room"])

    # ------------------------------------------------------------------------------
    # Insert REPEATING schedules (expand)
    # ------------------------------------------------------------------------------
    for row in repeating_schedules:
        start = datetime.datetime.strptime(row["start_date"], "%Y-%m-%d").date()
        end = datetime.datetime.strptime(row["end_date"], "%Y-%m-%d").date()
        repeat_n = int(row["repeat_integer"])

        time_str = row["time_str"]
        activity = row["activity"]
        auditor = row["auditor"]
        room = row["room"]

        for d, iso in zip(week_dates, date_strings):
            if d < start or d > end:
                continue

            delta_days = (d - start).days
            if delta_days % repeat_n == 0:
                day_name = date_to_day_name[iso]
                insert(day_name, time_str, activity, auditor, room)

    return output

@router.get("/api/files/get/{cfid}/scheduling/fetch/week/{date}")
@set_permission(["central_files", "dianetics"])
async def open_scheduling_page(request: Request, cfid:int, date:str):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is accessing the set scheduling for {cfid}")

    try:
        dateobj = datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse(
            content={
                "error": "Date format invalid."
            },
            status_code=400
        )
    
    schedule_data = get_scheduling_data(cfid, dateobj)
    
    return JSONResponse(
        content=schedule_data,
        status_code=200
    )

class ScheduleCellData(BaseModel):
    cfid: int
    time: str
    activity: str = ""
    auditor: str = ""
    room: str

@router.post("/api/files/get/{cfid}/scheduling/save/cell/{day}")
@set_permission(["central_files", "dianetics"])
async def set_scheduling_cell(
    request: Request, 
    cfid: int, 
    day: str, 
    postdata: ScheduleCellData
):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) editing schedule for CFID {cfid} on {day}")

    if not postdata.activity and not postdata.auditor and not postdata.room:
        return JSONResponse(
            content={
                "success": False,
                "error": "You need to fill out at least activity, room or auditor key. They're not both required, but one must be present."
            }
        )

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }
    
    # Gets the start of the week we are currently in
    datenow = datetime.datetime.now()
    week_start = datenow - datetime.timedelta(days=datenow.weekday())
    set_for_day_date = week_start + datetime.timedelta(weekdays[day.lower()])

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Ensure only one entry per time + room per day
        cur.execute(
            """
            SELECT activity, auditor, room, schedule_id FROM dn_schedule_data
            WHERE cfid = ? AND time_str = ? AND room = ?
            """,
            (cfid, postdata.time, postdata.room)
        )
        data = cur.fetchone()
        existing = data is not None

        activity = postdata.activity
        auditor = postdata.auditor
        room = postdata.room

        if not activity:
            try:
                activity = data[0]
            except TypeError:
                activity = None
        if not auditor:
            try:
                auditor = data[1]
            except TypeError:
                auditor = None
        if not room:
            return JSONResponse(
                content={"success": False, "error": "You did not specify 'room' (str) key."}
            )

        if existing:
            schedule_id = data[3]
            # Update existing entry
            cur.execute(
                """
                UPDATE dn_schedule_data
                SET activity = ?, auditor = ?, date = ?
                WHERE schedule_id = ?
                """,
                (activity, auditor, set_for_day_date, schedule_id)
            )
            logbook.info(f"Updated schedule cell {schedule_id}")
        else:
            # Insert new entry
            cur.execute("""
                INSERT INTO dn_schedule_data (cfid, time_str, activity, date, auditor, room)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cfid, postdata.time, postdata.activity, set_for_day_date, postdata.auditor, postdata.room))
            logbook.info("Inserted new schedule cell")

        conn.commit()

    return JSONResponse({"success": True, "message": "Schedule cell saved successfully."}, 200)

@router.get("/files/get/{cfid}/flags")
@set_permission("central_files")
async def open_flags_page(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is accessing the file flags for {cfid}")
    profile = centralfiles.get_profile(cfid=int(cfid))
    return templates.TemplateResponse(
        request,
        "flags.html",
        context={
            "profile": profile
        }
    )

# Note: Integration of below dianetics code may not be ideal. This was basically copy-pasted from the obsolete and deleted dianetics module.

class Dianetics_CF:
    @staticmethod
    def list_all_pcs():
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT cfid FROM cf_is_dianetics_pc WHERE is_dn_pc = True"
                )
                data = cursor.fetchall()
            except Exception as err:
                logbook.error(f"Error while fetching CF data: {err}", exception=err)
                return None

        parsed_data = []
        for item in data:
            with sqlite3.connect(DB_PATH) as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT name FROM cf_names WHERE cfid = ?",
                        (item[0],)
                    )
                    pc_name = cursor.fetchone()[0]
                except Exception as err:
                    logbook.error(f"Error while fetching PC name: {err}", exception=err)
                    continue

            parsed_data.append({"cfid": item[0], "name": pc_name})
        return parsed_data

    @staticmethod
    def get_preclear_data(cfid):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM cf_names WHERE cfid = ?",
                    (cfid,)
                )
                pc_name = cursor.fetchone()[0]
            except Exception as err:
                logbook.error(f"Error while fetching PC data: {err}", exception=err)

        return {
            "cfid": cfid,
            "name": pc_name,
        }

@router.get("/api/dianetics/preclear/list")
@set_permission(permission="dianetics")
async def list_preclears(request: Request):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) Is listing all preclears.")

    all_pcs = Dianetics_CF.list_all_pcs()

    if all_pcs is not None:
        return JSONResponse(
            content=all_pcs,
            status_code=200,
        )
    else:
        return JSONResponse(
            content={"error": "Error while fetching PC data."},
            status_code=500
        )

# Dianometry section
chart_to_db_map = {
    "B. Dianetic Evaluation": "dianetic_evaluation",
    "C. BEHAVIOR AND PHYSIOLOGY": "behavior_and_physiology",
    "D. PSYCHATRIC RANGE": "psychiatric_range",
    "E. MEDICAL RANGE": "medical_range",
    "F. EMOTION": "emotion",
    "G. AFFINITY": "affinity",
    "H. SONIC": "comm_sonic",
    "I. VISIO": "comm_visio",
    "J. SOMATIC": "comm_somatic",
    "K. SPEECH: TALKS\nSPEECH: LISTENS": "comm_speech_talks_listens",
    "L. SUBJECT'S HANDLING OF WRITTEN OR SPOKEN COMM WHEN ACTING AS A RELAY POINT": "handling_of_comm_as_relay",
    "M. REALITY (AGREEMENT)": "reality",
    "N. CONDITION OF TRACK AND VALENCES": "condition_track_valences",
    "O. MANIFESTATION OF ENGRAMS AND LOCKS": "manifestation_engrams_and_locks",
    # Note. This is not "sexual behavior toward children" It is "Sexual behavior (Are they violent during it for example,) and their attitude toward children."
    "P. SEXUAL BEHAVIOR\nATTITUDE TOWARD CHILDREN.": "sexual_behavior_and_attitude_to_children",
    "Q. COMMAND OVER ENVIRONMENT": "command_over_environ",
    "R. ACTUAL WORTH TO SOCIETY COMPARED TO APPARENT WORTH": "actual_worth_apparent_worth",
    "S. ETHIC LEVEL": "ethics_level",
    "T. HANDLING OF TRUTH": "handling_of_truth",
    "U. COURAGE LEVEL": "courage_level",
    "V. ABILITY TO HANDLE RESPONSIBILITY": "ability_handle_responsibility",
    "W. PERSISTENCE ON A GIVEN COURSE": "persistence_given_course",
    "X. LITERALNESS OF RECEPTION OF STATEMENTS": "literlness_with_which_statements_are_received",
    "Y. METHOD USED BY SUBJECT TO HANDLE OTHERS": "method_handle_others",
    "Z. COMMAND VALUE OF ACTION PHRASES": "command_value_action_phrases",
    "AB. Present time.": "present_time",
    "AC. Straight Memory.": "straight_memory",
    "AD. PLEASURE MOMENTS.": "pleasure_moments",
    "AE. IMAGINARY INCIDENTS.": "TEWRBA_imaginary_incidents",
    "AF. LOCKS.": "TEWRBA_locks",
    "AG. SCANNING LOCKS.": "TEWRBA_scanning_locks",
    "AH. SECONDARY ENGRAMS.": "TEWRBA_secondaries",
    "AI. ENGRAMS.": "TEWRBA_engrams",
    "AJ. CHAINS OF ENGRAMS.": "TEWRBA_Chains_engrams",
    "AK. CIRCUITS.": "circuits",
    "AL. CONDITION OF FILE CLERK.": "condition_file_clerk",
    "AM. HYPNOTIC LEVEL": "hypnotic_level",
    "AN. LEVEL OF MIND ALERT.": "level_mind_alert",
    "AO. RELATIVE ENTHETA ON CASE (APPROXIMATIONS).": "relative_entheta_on_case",
    "AP. ABILITY TO EXPERIENCE PRESENT TIME PLEASURE": "ability_pc_experience_ptp_pleasure",
    "AQ. TONE LEVEL OF AUDITOR NECESSARY TO HANDLE CASE.": "auditor_tone_needed",
    "AR. HOW TO AUDIT THE CASE.": "how_audit_case"
}

chart_columns = chart_to_db_map.keys()

@router.get("/api/dianetics/dianometry/get-chart/{cfid}")
@set_permission(permission="dianetics")
async def get_chart(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(
        f"IP {request.client.host} ({authbook.token_owner(token)}) is fetching the chart data for CFID {cfid}."
    )

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM CF_hubbard_chard_of_eval WHERE cfid = ?",
                (cfid,)
            )
            row = cursor.fetchone()
            if not row:
                return JSONResponse([], status_code=200)

            data = row[1:]  # skip cfid column, take the rest as tone levels
    except Exception as err:
        logbook.error(f"Error while fetching chart data: {err}")
        return JSONResponse([], status_code=500)

    # Transform into an array of {column_name, tone_level}
    response_data = []
    for i, column_name in enumerate(chart_columns):
        tone_level = data[i] if i < len(data) else None
        response_data.append({
            "column_name": column_name,
            "tone_level": str(tone_level) if tone_level is not None else None
        })

    return JSONResponse(response_data, status_code=200)

class update_chart_data(BaseModel):
    cfid: str
    column_name: str
    tone_level: str

def calculate_new_ts_position(cfid):
    """
    Calculate a PC's tone level by taking all of their positions on the chart
    and returning the most common tone level.
    """
    # Get all tone level positions for the CFID
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM CF_hubbard_chard_of_eval WHERE cfid = ?",
            (cfid,)
        )
        row = cursor.fetchone()
        if not row:
            return None  # CFID not found

    # Convert row to a list of tone levels (skip cfid column)
    tone_levels = [row[i + 1] for i in range(len(chart_columns)) if row[i + 1] is not None]

    if not tone_levels:
        return None

    # Find the most common tone level
    counter = Counter(tone_levels)
    most_common_tone, _ = counter.most_common(1)[0]

    return float(most_common_tone)

def update_tonescale_estimation(cfid):
    new_ts_position = calculate_new_ts_position(cfid)
    if new_ts_position is not None:
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO cf_tonescale_records (cfid, est_tone_level) VALUES (?, ?)
                    ON CONFLICT(cfid) DO UPDATE SET est_tone_level=excluded.est_tone_level
                    """,
                    (cfid, float(new_ts_position))
                )
                conn.commit()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while updating tone scale estimation: {err}", exception=err)
            conn.rollback()
            return
    else:
        logbook.warning(f"CFID {cfid} not found in CF_hubbard_chard_of_eval table.")

@router.post("/api/dianetics/dianometry/update-chart")
@set_permission(permission="dianetics")
async def update_chart(request: Request, data: update_chart_data):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is updating the chart data for CFID {data.cfid}, column {data.column_name}, tone level {data.tone_level}")

    if data.column_name not in chart_columns:
        return JSONResponse({"success": False, "error": "Invalid column name."}, status_code=400)

    column_name = chart_to_db_map[data.column_name]  # Convert to DB column name

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Note: Keep this secure and sanitised.
            cursor.execute(
                f"""
                INSERT INTO CF_hubbard_chard_of_eval (cfid, {column_name})
                VALUES (?, ?)
                ON CONFLICT(cfid) DO UPDATE SET {column_name}=excluded.{column_name}
                """,
                (data.cfid, data.tone_level)
            )
            conn.commit()

            update_tonescale_estimation(data.cfid)
            return JSONResponse({"success": True}, status_code=200)
    except sqlite3.OperationalError as err:
        logbook.error(f"Database error while updating chart data: {err}", exception=err)
        conn.rollback()
        return JSONResponse({"success": False, "error": "Database error occurred while updating chart data."}, status_code=500)

class dyn_strengths_data(BaseModel):
    cfid: int
    dynamic: str
    strength: str

dynamic_map = {
    "Self": 1,
    "Sex and Family": 2,
    "Groups": 3,
    "Mankind": 4
}

@router.post("/api/dianetics/dianometry/dyn_strengths/set")
@set_permission(permission="dianetics")
async def dyn_strengths(request: Request, data: dyn_strengths_data):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is setting dyn strengths for {data.cfid}.")

    dyn_strength = int(data.strength)
    dyn_number = dynamic_map[data.dynamic]

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO cf_dynamic_strengths (cfid, dyn_{dyn_number})
                VALUES (?, ?)
                ON CONFLICT(cfid) DO UPDATE SET dyn_{dyn_number}=excluded.dyn_{dyn_number}
                """,
                (data.cfid, dyn_strength,)
            )
            conn.commit()
            update_mind_class_estimation(data.cfid)
            return JSONResponse({"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while updating dyn strengths: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while updating dyn strengths."}, status_code=500)

@router.get("/api/dianetics/dianometry/dyn_strengths/get/{cfid}")
@set_permission(permission="dianetics")
async def get_dyn_strengths(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is getting all dyn strengths for {cfid}.")

    update_mind_class_estimation(cfid)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT dyn_1, dyn_2, dyn_3, dyn_4 FROM cf_dynamic_strengths WHERE cfid = ?",
                (cfid,)
            )
            data = cur.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching dyn strengths: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"error": "Database error occurred while fetching dyn strengths."}, status_code=500)

    if data is None:
        return JSONResponse([
            {"dynamic": 1, "strength": 0},
            {"dynamic": 2, "strength": 0},
            {"dynamic": 3, "strength": 0},
            {"dynamic": 4, "strength": 0}
        ], status_code=200)

    parsed_data = []
    dyn_counter = 0
    for dynamic in data:
        dyn_counter += 1
        parsed_data.append({
            "dynamic": dyn_counter,
            "strength": dynamic if dynamic else 0
        })
    return JSONResponse(parsed_data, status_code=200)

class shutoffs_data(BaseModel):
    cfid: int
    name: str
    state: bool

@router.post("/api/dianetics/dianometry/shutoffs/set")
@set_permission(permission="dianetics")
async def set_shutoffs(request: Request, data: shutoffs_data):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is setting shutoff {data.name} for {data.cfid} to {data.state}.")

    update_mind_class_estimation(data.cfid)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO cf_dn_shutoffs (cfid, {data.name}_shutoff)
                VALUES (?, ?)
                ON CONFLICT(cfid) DO UPDATE SET {data.name}_shutoff=excluded.{data.name}_shutoff
                """,
                (data.cfid, data.state,)
            )
            conn.commit()
            return JSONResponse({"success": True}, status_code=200)
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while updating shutoffs: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"success": False, "error": "Database error occurred while updating shutoffs."}, status_code=500)

@router.get("/api/dianetics/dianometry/shutoffs/get/{cfid}")
@set_permission(permission=["dianetics", "central_files"])
async def get_shutoffs(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is getting all shutoffs for {cfid}.")

    try:
        # We update it here and now incase the values were changed elsewhere
        update_mind_class_estimation(cfid)
    except Exception as err:
        logbook.error(f"Error while updating mind class estimation: {err}", exception=err)

    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT sonic_shutoff, visio_shutoff FROM cf_dn_shutoffs WHERE cfid = ?",
                (cfid,)
            )
            data = cur.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching shutoffs: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"error": "Database error occurred while fetching shutoffs."}, status_code=500)

    try:
        sonic_shutoff = bool(data[0])
    except TypeError:
        sonic_shutoff = False
    try:
        visio_shutoff = bool(data[1])
    except TypeError:
        visio_shutoff = False

    return JSONResponse([
        {"name": "sonic", "state": sonic_shutoff},
        {"name": "visio", "state": visio_shutoff}
    ], status_code=200)

mind_level_map = {
    1: "Class A",
    2: "Class B",
    3: "Class C"
}

@router.get("/api/dianetics/dianometry/get_mind_class/{cfid}")
@set_permission(permission=["dianetics", "central_files"])
async def get_mind_class(request: Request, cfid):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host} ({authbook.token_owner(token)}) is getting mind class for {cfid}.")
    # Very often when getting mind class, other values have changed. So we update it here.
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT actual_class, apparent_class FROM cf_pc_mind_class WHERE cfid = ?",
                (cfid,)
            )
            data = cur.fetchone()
        except sqlite3.OperationalError as err:
            logbook.error(f"Database error while fetching mind class: {err}", exception=err)
            conn.rollback()
            return JSONResponse({"error": "Database error occurred while fetching mind class."}, status_code=500)

    if not data:
        return JSONResponse({"error": "Mind class not found."}, status_code=404)
    else:
        return JSONResponse({
            "actual": mind_level_map[int(data[0])],
            "apparent": mind_level_map[int(data[1])]
            },
            status_code=200
        )
    
from library.email import client_email, recipient_profile

@router.get("/files/get/{cfid}/mail", response_class=HTMLResponse)
@set_permission(permission=['central_files', 'mail_view'])
async def show_mail_page(request: Request, cfid:int):
    token:str = route_prechecks(request)
    logbook.info(f"IP {request.client.host}, User {authbook.token_owner(token)} has accessed the C/F Emailing page for {cfid}.")
    return templates.TemplateResponse(
        request,
        "mail.html",
        {
            "profile": centralfiles.get_profile(cfid=cfid)
        }
    )

class send_mail_data(BaseModel):
    message: str
    subject_line: str

@router.post("/api/files/{cfid}/mail/send", response_class=HTMLResponse)
@set_permission(permission=['central_files', 'mail_send', 'mail_view'])
async def mail_user(request: Request, cfid:int, data: send_mail_data):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is sending mail to CFID {cfid}")
    profile = await get_cached_profile(cfid)
    mail_address = profile['email_addr']

    client = client_email(
        recipient=recipient_profile(
            email=mail_address,
            subjectline=data.subject_line,
            message=data.message
        )
    )
    
    result = client.send()
    return HTMLResponse(str(result is not False), 200)

@router.get("/files/mailing", response_class=HTMLResponse)
@set_permission(permission=['central_files', 'mail_view'])
async def show_mail_page(request: Request):
    token:str = route_prechecks(request)
    username = authbook.token_owner(token)
    is_admin = authbook.is_user_admin(username)
    logbook.info(f"IP {request.client.host}, User {username} has accessed the C/F Bulk Emailing page.")
    return templates.TemplateResponse(
        request,
        "mailing.html",
        {
            'user': username,
            'user_is_admin': is_admin
        }
    )

class send_bulk_mail_data(BaseModel):
    recipients: list

@router.post("/api/files/mail/bulksend", response_class=HTMLResponse)
@set_permission(permission=['central_files', 'mail_send', 'mail_bulk_send', 'mail_view'])
async def mail_user(request: Request, data: send_bulk_mail_data):
    token:str = route_prechecks(request)
    logbook.info(f"{request.client.host} ({authbook.token_owner(token)}) Is bulk-mailing.")

    recipients_list = []

    for recipient in data.recipients:
        recipient=recipient_profile(
            email=recipient['email_address'],
            subjectline=recipient['subject_line'],
            message=recipient['message']
        )
        recipients_list.append(recipient)

    client = client_email(
        recipients=recipients_list
    )
    
    result = client.send()
    return HTMLResponse(str(result is not False), 200)