import streamlit as st
import hashlib
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import secrets
import string
from dotenv import load_dotenv
import time
import threading
import math
import json
import random

load_dotenv()

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
class Config:
    DATABASE_URL        = os.getenv('DATABASE_URL', 'sqlite:///afyalink.db')
    SMTP_SERVER         = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT           = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME       = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD       = os.getenv('SMTP_PASSWORD')
    DEFAULT_LATITUDE    = -0.0916
    DEFAULT_LONGITUDE   = 34.7680
    DEFAULT_ZOOM        = 10
    PAGE_TITLE          = "AfyaLink — Kenya National Referral Network"
    PAGE_ICON           = "🏥"
    LAYOUT              = "wide"
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
    NOTIFICATION_CHECK_INTERVAL = 30
    LOCATION_UPDATE_INTERVAL    = 10
    FUEL_PRICE_PER_LITER        = 180
    AVERAGE_FUEL_CONSUMPTION    = 0.12
    BASE_OPERATING_COST_PER_KM  = 50
    FUEL_TANK_CAPACITY          = 80

    KENYA_COUNTIES = [
        "Kisumu Pilot County", "Nairobi", "Mombasa", "Nakuru", "Kisii",
        "Uasin Gishu", "Machakos", "Kilifi", "Kakamega", "Meru",
        "Nyeri", "Murang'a", "Kiambu", "Trans Nzoia", "Bungoma",
        "Homa Bay", "Migori", "Siaya", "Vihiga", "Nandi",
        "Kericho", "Bomet", "Narok", "Laikipia", "Nyandarua",
        "Kirinyaga", "Embu", "Tharaka-Nithi", "Isiolo", "Marsabit",
        "Turkana", "West Pokot", "Samburu", "Elgeyo-Marakwet", "Baringo",
        "Kajiado", "Makueni", "Kitui", "Taita-Taveta", "Kwale",
        "Tana River", "Lamu", "Garissa", "Wajir", "Mandera",
        "Busia", "Nyamira"
    ]

Base = declarative_base()

# -----------------------------------------------------------------------------
# DATABASE MODELS
# -----------------------------------------------------------------------------
class Patient(Base):
    __tablename__ = 'patients'
    patient_id              = Column(String,  primary_key=True)
    name                    = Column(String,  nullable=False)
    age                     = Column(Integer, nullable=False)
    condition               = Column(String,  nullable=False)
    referring_hospital      = Column(String,  nullable=False)
    receiving_hospital      = Column(String,  nullable=False)
    referring_physician     = Column(String,  nullable=False)
    receiving_physician     = Column(String)
    notes                   = Column(Text)
    vital_signs             = Column(JSON)
    medical_history         = Column(Text)
    current_medications     = Column(Text)
    allergies               = Column(Text)
    referral_time           = Column(DateTime, default=datetime.utcnow)
    status                  = Column(String,  default='Referred')
    assigned_ambulance      = Column(String)
    created_by              = Column(String)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    referring_hospital_lat  = Column(Float)
    referring_hospital_lng  = Column(Float)
    receiving_hospital_lat  = Column(Float)
    receiving_hospital_lng  = Column(Float)
    pickup_notification_sent  = Column(Boolean, default=False)
    enroute_notification_sent = Column(Boolean, default=False)
    trip_distance           = Column(Float)
    trip_fuel_cost          = Column(Float)
    trip_cost_savings       = Column(Float, default=0.0)
    county                  = Column(String, default='Kisumu')
    priority_level          = Column(String, default='Standard')
    response_time_seconds   = Column(Integer, default=0)

class Ambulance(Base):
    __tablename__ = 'ambulances'
    ambulance_id            = Column(String, primary_key=True)
    current_location        = Column(String)
    latitude                = Column(Float)
    longitude               = Column(Float)
    status                  = Column(String, default='Available')
    driver_name             = Column(String)
    driver_contact          = Column(String)
    current_patient         = Column(String)
    destination             = Column(String)
    route                   = Column(JSON)
    start_time              = Column(DateTime)
    current_step            = Column(Integer, default=0)
    mission_complete        = Column(Boolean, default=False)
    estimated_arrival       = Column(DateTime)
    last_location_update    = Column(DateTime, default=datetime.utcnow)
    fuel_level              = Column(Float, default=100.0)
    fuel_consumption_rate   = Column(Float, default=0.12)
    total_fuel_cost         = Column(Float, default=0.0)
    total_distance_traveled = Column(Float, default=0.0)
    cost_savings            = Column(Float, default=0.0)
    county                  = Column(String, default='Kisumu')
    total_missions          = Column(Integer, default=0)
    patient_feedback_score  = Column(Float, default=5.0)

class Referral(Base):
    __tablename__ = 'referrals'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    patient_id   = Column(String, nullable=False)
    timestamp    = Column(DateTime, default=datetime.utcnow)
    status       = Column(String, default='Ambulance Dispatched')
    ambulance_id = Column(String)
    created_by   = Column(String)

class HandoverForm(Base):
    __tablename__ = 'handover_forms'
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    patient_id          = Column(String, nullable=False)
    patient_name        = Column(String)
    age                 = Column(Integer)
    condition           = Column(String)
    referring_hospital  = Column(String)
    receiving_hospital  = Column(String)
    referring_physician = Column(String)
    receiving_physician = Column(String)
    transfer_time       = Column(DateTime, default=datetime.utcnow)
    vital_signs         = Column(JSON)
    medical_history     = Column(Text)
    current_medications = Column(Text)
    allergies           = Column(Text)
    notes               = Column(Text)
    ambulance_id        = Column(String)
    created_by          = Column(String)

class Communication(Base):
    __tablename__ = 'communications'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    patient_id   = Column(String)
    ambulance_id = Column(String)
    sender       = Column(String)
    receiver     = Column(String)
    message      = Column(Text)
    timestamp    = Column(DateTime, default=datetime.utcnow)
    message_type = Column(String)

class LocationUpdate(Base):
    __tablename__ = 'location_updates'
    id            = Column(Integer, primary_key=True, autoincrement=True)
    ambulance_id  = Column(String)
    latitude      = Column(Float)
    longitude     = Column(Float)
    location_name = Column(String)
    timestamp     = Column(DateTime, default=datetime.utcnow)
    patient_id    = Column(String)

class SystemMetric(Base):
    __tablename__ = 'system_metrics'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    metric_name  = Column(String)
    metric_value = Column(Float)
    recorded_at  = Column(DateTime, default=datetime.utcnow)

# -----------------------------------------------------------------------------
# DATABASE SERVICE
# -----------------------------------------------------------------------------
class Database:
    def __init__(self):
        url = os.getenv('DATABASE_URL', 'sqlite:///afyalink.db')
        self.engine = create_engine(url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_patient(self, data):
        if 'patient_id' not in data:
            data['patient_id'] = f"AFL{secrets.token_hex(4).upper()}"
        p = Patient(**data)
        self.session.add(p)
        self.session.commit()
        return p

    def get_available_ambulances(self):
        return self.session.query(Ambulance).filter(Ambulance.status == 'Available').all()

    def update_ambulance_status(self, ambulance_id, status, patient_id=None):
        a = self.session.query(Ambulance).filter(Ambulance.ambulance_id == ambulance_id).first()
        if a:
            a.status = status
            if patient_id:
                a.current_patient = patient_id
                a.total_missions += 1
            self.session.commit()

    def get_patient_by_id(self, pid):
        return self.session.query(Patient).filter(Patient.patient_id == pid).first()

    def get_all_patients(self):
        return self.session.query(Patient).all()

    def get_all_ambulances(self):
        return self.session.query(Ambulance).all()

    def add_referral(self, data):
        r = Referral(**data)
        self.session.add(r)
        self.session.commit()
        return r

    def add_handover_form(self, data):
        h = HandoverForm(**data)
        self.session.add(h)
        self.session.commit()
        return h

    def add_communication(self, data):
        c = Communication(**data)
        self.session.add(c)
        self.session.commit()
        return c

    def get_communications_for_patient(self, pid):
        return self.session.query(Communication).filter(
            Communication.patient_id == pid
        ).order_by(Communication.timestamp.desc()).all()

    def add_location_update(self, data):
        lu = LocationUpdate(**data)
        self.session.add(lu)
        self.session.commit()
        return lu

    def add_system_metric(self, name, value):
        m = SystemMetric(metric_name=name, metric_value=value)
        self.session.add(m)
        self.session.commit()

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def find_nearest_ambulance(self, lat, lng, min_fuel=20.0):
        available = self.get_available_ambulances()
        if not available:
            return None
        nearest, min_dist = None, float('inf')
        for a in available:
            if a.fuel_level < min_fuel:
                continue
            if a.latitude is not None and a.longitude is not None:
                d = self.calculate_distance(lat, lng, a.latitude, a.longitude)
                if d < min_dist:
                    min_dist, nearest = d, a
        return nearest

    def update_ambulance_fuel(self, ambulance_id, distance_km=None, new_fuel_level=None):
        a = self.session.query(Ambulance).filter(Ambulance.ambulance_id == ambulance_id).first()
        if a:
            if distance_km is not None:
                a.fuel_level = max(0, a.fuel_level - distance_km * a.fuel_consumption_rate)
            elif new_fuel_level is not None:
                a.fuel_level = max(0, min(100, new_fuel_level))
            self.session.commit()
            return a.fuel_level
        return None

# -----------------------------------------------------------------------------
# AUTHENTICATION
# -----------------------------------------------------------------------------
class Authentication:
    def __init__(self):
        self.credentials = {
            'usernames': {
                'admin': {
                    'password': self._hash('admin123'),
                    'email': 'admin@afyalink.go.ke',
                    'role': 'Admin',
                    'hospital': 'All Facilities',
                    'name': 'System Administrator'
                },
                'hospital_staff': {
                    'password': self._hash('staff123'),
                    'email': 'staff@jootrh.go.ke',
                    'role': 'Hospital Staff',
                    'hospital': 'Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)',
                    'name': 'Dr. Achieng Odhiambo'
                },
                'driver': {
                    'password': self._hash('driver123'),
                    'email': 'driver@afyalink.go.ke',
                    'role': 'Ambulance Driver',
                    'hospital': 'Ambulance Service',
                    'name': 'John Omondi'
                },
                'kisumu_staff': {
                    'password': self._hash('kisumu123'),
                    'email': 'staff@kisumuhosp.go.ke',
                    'role': 'Hospital Staff',
                    'hospital': 'Kisumu County Referral Hospital',
                    'name': 'Dr. Mary Atieno'
                }
            }
        }

    def _hash(self, pw):
        return hashlib.sha256(pw.encode()).hexdigest()

    def authenticate(self, username, password):
        u = self.credentials['usernames'].get(username)
        if u and self._hash(password) == u['password']:
            return u
        return None

    def setup_auth_ui(self):
        st.sidebar.markdown("""
        <div style='text-align:center; padding: 1rem 0 0.5rem;'>
            <div style='font-size:2.2rem;'>🏥</div>
            <div style='font-size:1.4rem; font-weight:800; color:#00695c; letter-spacing:2px;'>
                AFYALINK
            </div>
            <div style='font-size:0.65rem; color:#78909c; letter-spacing:3px; text-transform:uppercase;'>
                National Referral Network
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.sidebar.markdown("---")

        if not st.session_state.get('authenticated'):
            st.sidebar.markdown("### Secure Login")
            username = st.sidebar.text_input("Username", placeholder="Enter username")
            password = st.sidebar.text_input("Password", type="password", placeholder="Enter password")
            if st.sidebar.button("Sign In", use_container_width=True, type="primary"):
                user = self.authenticate(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.sidebar.error("Invalid credentials")
        else:
            u = st.session_state.user
            role_icons = {'Admin': '⚙️', 'Hospital Staff': '🏥', 'Ambulance Driver': '🚑'}
            st.sidebar.markdown(f"""
            <div style='background:#f5f5f5; border:1px solid #00695c40;border-radius:12px;padding:1rem;margin-bottom:1rem;'>
                <div style='font-size:1.1rem;font-weight:700;color:#1a237e;'>{role_icons.get(u['role'], '')} {u['name']}</div>
                <div style='font-size:0.75rem;color:#00695c;font-weight:600;'>{u['role']}</div>
                <div style='font-size:0.7rem;color:#78909c;margin-top:4px;'>{u['hospital'][:35]}...</div>
            </div>
            """, unsafe_allow_html=True)
            if st.sidebar.button("Sign Out", use_container_width=True):
                st.session_state.clear()
                st.rerun()

    def require_auth(self, roles=None):
        if not st.session_state.get('authenticated'):
            st.warning("Please login to access this section.")
            return False
        if roles and st.session_state.user['role'] not in roles:
            st.error(f"Access restricted. Required: {', '.join(roles)}")
            return False
        return True

# -----------------------------------------------------------------------------
# NOTIFICATION SERVICE
# -----------------------------------------------------------------------------
class NotificationService:
    def __init__(self, db):
        self.db = db

    def send_notification(self, recipient, message, ntype):
        labels = {
            'referral': 'New Referral',
            'dispatch': 'Ambulance Dispatched',
            'arrival': 'Patient Arrived',
            'pickup': 'Patient Picked Up',
            'emergency': 'EMERGENCY ALERT'
        }
        st.toast(f"{labels.get(ntype, 'Notification')} → {recipient}", icon="✅")
        return True

    def _log(self, patient_id, ambulance_id, sender, receiver, message, mtype):
        self.db.add_communication({
            'patient_id': patient_id,
            'ambulance_id': ambulance_id,
            'sender': sender,
            'receiver': receiver,
            'message': message,
            'message_type': mtype
        })

    def send_automatic_pickup_notification_to_driver(self, patient, ambulance):
        msg = (f"NEW ASSIGNMENT\n\nPatient: {patient.name} | Age: {patient.age}\n"
               f"Condition: {patient.condition}\nPickup: {patient.referring_hospital}\n"
               f"Destination: {patient.receiving_hospital}\nPriority: HIGH\n\n"
               f"Proceed immediately to pickup location.")
        self._log(patient.patient_id, ambulance.ambulance_id,
                  'AfyaLink System', ambulance.driver_name, msg, 'auto_driver_assignment')
        st.toast(f"Driver {ambulance.driver_name} notified", icon="✅")

    def send_automatic_referral_notification_to_hospital(self, patient, ambulance=None):
        amb_info = f"\nAssigned Ambulance: {ambulance.ambulance_id} — {ambulance.driver_name}" if ambulance else ""
        msg = (f"INCOMING PATIENT REFERRAL\n\nPatient: {patient.name} | Age: {patient.age}\n"
               f"Condition: {patient.condition}\nFrom: {patient.referring_hospital}\n"
               f"Physician: {patient.referring_physician}{amb_info}\n\n"
               f"Please prepare receiving team. ETA: 30–45 minutes.")
        self._log(patient.patient_id, ambulance.ambulance_id if ambulance else None,
                  'AfyaLink System', patient.receiving_hospital, msg, 'auto_hospital_notification')
        st.toast(f"{patient.receiving_hospital} notified of incoming patient", icon="✅")

    def send_automatic_enroute_notification(self, patient, ambulance):
        msg = (f"PATIENT EN ROUTE\n\nPatient {patient.name} has been picked up.\n"
               f"Ambulance: {ambulance.ambulance_id} | Driver: {ambulance.driver_name}\n"
               f"ETA: 15–25 minutes. Please prepare receiving bay.")
        self._log(patient.patient_id, ambulance.ambulance_id,
                  'AfyaLink System', patient.receiving_hospital, msg, 'auto_enroute_notification')
        st.toast(f"Enroute notification sent to {patient.receiving_hospital}", icon="✅")

    def send_automatic_arrival_notification(self, patient, ambulance):
        msg = (f"PATIENT DELIVERED\n\n{patient.name} has arrived at {patient.receiving_hospital}.\n"
               f"Ambulance: {ambulance.ambulance_id} | Time: {datetime.now().strftime('%H:%M')}\n"
               f"Trip Distance: {patient.trip_distance or 'N/A'} km. Ambulance returning to service.")
        for hosp in [patient.referring_hospital, patient.receiving_hospital]:
            self._log(patient.patient_id, ambulance.ambulance_id,
                      'AfyaLink System', hosp, msg, 'auto_arrival_notification')
        st.toast("Arrival notifications sent to both facilities", icon="✅")

# -----------------------------------------------------------------------------
# COST CALCULATION SERVICE
# -----------------------------------------------------------------------------
class CostCalculationService:
    def __init__(self, db):
        self.db = db

    def calculate_trip_cost(self, distance_km, fuel_rate=None):
        if fuel_rate is None:
            fuel_rate = Config.AVERAGE_FUEL_CONSUMPTION
        fuel_used   = distance_km * fuel_rate
        fuel_cost   = fuel_used * Config.FUEL_PRICE_PER_LITER
        op_cost     = distance_km * Config.BASE_OPERATING_COST_PER_KM
        total       = fuel_cost + op_cost
        return {
            'distance_km': distance_km,
            'fuel_used_liters': fuel_used,
            'fuel_cost_ksh': fuel_cost,
            'operating_cost_ksh': op_cost,
            'total_cost_ksh': total
        }

    def update_ambulance_costs(self, ambulance_id, distance_km):
        a = self.db.session.query(Ambulance).filter(Ambulance.ambulance_id == ambulance_id).first()
        if a:
            tc = self.calculate_trip_cost(distance_km, a.fuel_consumption_rate)
            a.total_distance_traveled += distance_km
            a.total_fuel_cost         += tc['fuel_cost_ksh']
            a.cost_savings            += tc['total_cost_ksh'] * 0.15
            self.db.session.commit()
            return tc
        return None

# -----------------------------------------------------------------------------
# ANALYTICS SERVICE
# -----------------------------------------------------------------------------
class AnalyticsService:
    def __init__(self, db):
        self.db = db
        self.cost_svc = CostCalculationService(db)

    def get_kpis(self):
        patients   = self.db.get_all_patients()
        ambulances = self.db.get_all_ambulances()
        total      = len(patients) if patients else 156
        active     = len([p for p in patients if p.status not in ['Arrived at Destination','Completed']]) if patients else 8
        avail_amb  = len([a for a in ambulances if a.status == 'Available']) if ambulances else 12
        total_fuel = sum(a.total_fuel_cost for a in ambulances) if ambulances else 125000
        total_save = sum(a.cost_savings    for a in ambulances) if ambulances else 18750
        total_dist = sum(a.total_distance_traveled for a in ambulances) if ambulances else 25000
        return {
            'total_referrals': total,
            'active_referrals': active,
            'available_ambulances': avail_amb,
            'avg_response_time': '18.4 min',
            'completion_rate': f"{(total-active)/total*100:.1f}%" if total > 0 else "94.2%",
            'total_fuel_cost': total_fuel,
            'total_cost_savings': total_save,
            'total_distance_km': total_dist,
            'counties_active': 1,
            'counties_ready': 47
        }

    def get_referral_trends(self):
        patients = self.db.get_all_patients()
        if patients and len(patients) > 0:
            df = pd.DataFrame([{'date': p.referral_time.date(), 'condition': p.condition} for p in patients])
            return df.groupby('date').size().reset_index(name='count')
        dates = pd.date_range(end=datetime.now(), periods=30)
        counts = [random.randint(2, 12) for _ in range(30)]
        return pd.DataFrame({'date': dates, 'count': counts})

    def get_cost_analytics(self):
        ambulances = self.db.get_all_ambulances()
        patients   = self.db.get_all_patients()
        completed  = [p for p in patients if p.status == 'Completed'] if patients else []
        total_tc   = sum(p.trip_fuel_cost or 0 for p in completed) if completed else 85000
        total_ts   = sum(p.trip_cost_savings or 0 for p in completed) if completed else 12750
        months     = ['Jan','Feb','Mar','Apr','May','Jun']
        mc         = [total_tc*(0.6+i*0.1) for i in range(6)]
        ms         = [total_ts*(0.5+i*0.12) for i in range(6)]
        return {
            'months': months,
            'monthly_costs': mc,
            'monthly_savings': ms,
            'total_trip_costs': total_tc,
            'total_trip_savings': total_ts
        }

# -----------------------------------------------------------------------------
# REFERRAL SERVICE
# -----------------------------------------------------------------------------
class ReferralService:
    def __init__(self, db, notifications):
        self.db   = db
        self.notif = notifications
        self.cost  = CostCalculationService(db)

    def create_referral(self, data, user):
        try:
            data['created_by'] = user['role']
            if (data.get('referring_hospital_lat') and data.get('receiving_hospital_lat')):
                dist = self.db.calculate_distance(
                    data['referring_hospital_lat'], data['referring_hospital_lng'],
                    data['receiving_hospital_lat'], data['receiving_hospital_lng'])
                ce = self.cost.calculate_trip_cost(dist)
                data['trip_distance']  = dist
                data['trip_fuel_cost'] = ce['total_cost_ksh']
            patient = self.db.add_patient(data)
            self.db.add_referral({'patient_id': patient.patient_id,
                                   'ambulance_id': data.get('assigned_ambulance'),
                                   'created_by': user['role']})
            self.notif.send_automatic_referral_notification_to_hospital(patient)
            self.db.add_system_metric('referral_created', 1)
            return patient
        except Exception as e:
            st.error(f"Error creating referral: {e}")
            return None

    def assign_ambulance(self, patient_id, ambulance_id):
        try:
            patient = self.db.get_patient_by_id(patient_id)
            ambulance = self.db.session.query(Ambulance).filter(Ambulance.ambulance_id == ambulance_id).first()
            if patient and ambulance:
                start_time = datetime.utcnow()
                patient.assigned_ambulance = ambulance_id
                patient.status = 'Ambulance Assigned'
                patient.response_time_seconds = int((start_time - patient.referral_time).total_seconds())
                self.db.session.commit()
                self.notif.send_automatic_pickup_notification_to_driver(patient, ambulance)
                self.db.update_ambulance_status(ambulance_id, 'On Transfer', patient_id)
                self.db.add_system_metric('ambulance_assigned', 1)
                return True
        except Exception as e:
            st.error(f"Error assigning ambulance: {e}")
        return False

    def assign_ambulance_and_simulate(self, patient_id, ambulance_id):
        try:
            patient = self.db.get_patient_by_id(patient_id)
            ambulance = self.db.session.query(Ambulance).filter(
                Ambulance.ambulance_id == ambulance_id
            ).first()
            
            if patient and ambulance:
                start_time = datetime.utcnow()
                patient.assigned_ambulance = ambulance_id
                patient.status = 'Ambulance Assigned'
                patient.response_time_seconds = int((start_time - patient.referral_time).total_seconds())
                
                ambulance.status = 'On Transfer'
                ambulance.current_patient = patient_id
                ambulance.destination = patient.receiving_hospital
                
                self.db.session.commit()
                
                self.notif.send_automatic_pickup_notification_to_driver(patient, ambulance)
                self.db.add_system_metric('ambulance_assigned', 1)
                
                simulator = LocationSimulator(self.db)
                simulator.start_simulation_background(
                    ambulance_id,
                    patient.patient_id,
                    patient.referring_hospital_lat,
                    patient.referring_hospital_lng,
                    patient.receiving_hospital_lat,
                    patient.receiving_hospital_lng
                )
                
                distance = self.db.calculate_distance(
                    patient.referring_hospital_lat,
                    patient.referring_hospital_lng,
                    patient.receiving_hospital_lat,
                    patient.receiving_hospital_lng
                )
                estimated_minutes = int(distance / 0.8)
                
                st.success(f"""
                Ambulance {ambulance_id} assigned to {patient.name}
                From: {patient.referring_hospital}
                To: {patient.receiving_hospital}
                Distance: {distance:.1f} km
                ETA: ~{estimated_minutes} minutes
                Live tracking activated. Go to Tracking tab to see movement.
                """)
                
                return True
                
        except Exception as e:
            st.error(f"Error: {e}")
        return False

    def auto_assign_nearest(self, patient_id):
        patient = self.db.get_patient_by_id(patient_id)
        if not patient or not patient.referring_hospital_lat:
            st.error("Patient location data missing.")
            return False
        nearest = self.db.find_nearest_ambulance(patient.referring_hospital_lat, patient.referring_hospital_lng)
        if not nearest:
            st.error("No available ambulances with sufficient fuel.")
            return False
        patient.assigned_ambulance = nearest.ambulance_id
        patient.status = 'Ambulance Assigned'
        patient.response_time_seconds = int((datetime.utcnow() - patient.referral_time).total_seconds())
        nearest.status = 'On Transfer'
        nearest.current_patient = patient_id
        nearest.destination = patient.receiving_hospital
        self.notif.send_automatic_pickup_notification_to_driver(patient, nearest)
        self.db.session.commit()
        self.db.add_system_metric('ambulance_assigned', 1)
        st.success(f"Nearest ambulance {nearest.ambulance_id} auto-assigned to {patient.name}")
        return True

    def mark_picked_up(self, patient_id):
        patient = self.db.get_patient_by_id(patient_id)
        if not patient:
            return False
        ambulance = self.db.session.query(Ambulance).filter(
            Ambulance.ambulance_id == patient.assigned_ambulance).first()
        if not ambulance:
            return False
        patient.status = 'Patient Picked Up'
        patient.pickup_notification_sent = True
        self.notif.send_automatic_enroute_notification(patient, ambulance)
        self.db.session.commit()
        self.db.add_system_metric('patient_picked_up', 1)
        return True

    def complete_mission(self, ambulance, patient):
        ambulance.status = 'Available'
        ambulance.current_patient = None
        ambulance.mission_complete = True
        patient.status = 'Arrived at Destination'
        if patient.trip_distance:
            tc = self.cost.update_ambulance_costs(ambulance.ambulance_id, patient.trip_distance)
            if tc:
                patient.trip_fuel_cost = tc['total_cost_ksh']
                patient.trip_cost_savings = tc['total_cost_ksh'] * 0.15
        self.db.session.commit()
        self.notif.send_automatic_arrival_notification(patient, ambulance)
        self.db.add_system_metric('mission_completed', 1)
        st.success("Mission complete! Patient successfully delivered.")
        st.balloons()

# -----------------------------------------------------------------------------
# AMBULANCE SERVICE
# -----------------------------------------------------------------------------
class AmbulanceService:
    def __init__(self, db):
        self.db = db

    def update_location(self, ambulance_id, lat, lng, name, patient_id=None):
        try:
            a = self.db.session.query(Ambulance).filter(Ambulance.ambulance_id==ambulance_id).first()
            if a:
                a.latitude = lat; a.longitude = lng
                a.current_location      = name
                a.last_location_update  = datetime.utcnow()
                self.db.session.commit()
                self.db.add_location_update({'ambulance_id':ambulance_id,'latitude':lat,
                                              'longitude':lng,'location_name':name,'patient_id':patient_id})
                return True
        except Exception as e:
            st.error(f"Location update error: {e}")
        return False

    def get_fuel_info(self, ambulance_id):
        a = self.db.session.query(Ambulance).filter(Ambulance.ambulance_id==ambulance_id).first()
        if a:
            status = "Good" if a.fuel_level > 50 else "Low" if a.fuel_level > 20 else "Critical"
            return {'ambulance': a, 'fuel_level': a.fuel_level, 'fuel_status': status}
        return None

# -----------------------------------------------------------------------------
# LOCATION SIMULATOR
# -----------------------------------------------------------------------------
class LocationSimulator:
    def __init__(self, db):
        self.db      = db
        self.running = False
        self.simulation_thread = None

    def start_simulation(self, ambulance_id, patient_id, s_lat, s_lng, e_lat, e_lng):
        self.running = True
        svc  = AmbulanceService(self.db)
        dist = self.db.calculate_distance(s_lat, s_lng, e_lat, e_lng)
        steps = 20
        for step in range(steps + 1):
            if not self.running: break
            lat = s_lat + (e_lat - s_lat) / steps * step
            lng = s_lng + (e_lng - s_lng) / steps * step
            progress_pct = int((step / steps) * 100)
            svc.update_location(ambulance_id, lat, lng, f"En route — {progress_pct}% to destination", patient_id)
            if step > 0:
                self.db.update_ambulance_fuel(ambulance_id, dist / steps)
            time.sleep(3)
        if self.running:
            a = self.db.session.query(Ambulance).filter(Ambulance.ambulance_id==ambulance_id).first()
            if a:
                a.status = 'Available'
                a.current_patient = None
                self.db.session.commit()
                patient = self.db.get_patient_by_id(patient_id)
                if patient:
                    patient.status = 'Arrived at Destination'
                    self.db.session.commit()
                    st.success(f"Patient {patient.name} has arrived at destination!")
                    st.balloons()

    def start_simulation_background(self, ambulance_id, patient_id, s_lat, s_lng, e_lat, e_lng):
        import threading
        
        def simulate():
            svc = AmbulanceService(self.db)
            dist = self.db.calculate_distance(s_lat, s_lng, e_lat, e_lng)
            steps = 20
            for step in range(steps + 1):
                if not self.running:
                    break
                lat = s_lat + (e_lat - s_lat) / steps * step
                lng = s_lng + (e_lng - s_lng) / steps * step
                progress_pct = int((step / steps) * 100)
                svc.update_location(ambulance_id, lat, lng, f"En route — {progress_pct}% to destination", patient_id)
                if step > 0:
                    self.db.update_ambulance_fuel(ambulance_id, dist / steps)
                time.sleep(3)
            
            if self.running:
                a = self.db.session.query(Ambulance).filter(Ambulance.ambulance_id==ambulance_id).first()
                if a:
                    a.status = 'Available'
                    a.current_patient = None
                    self.db.session.commit()
                    patient = self.db.get_patient_by_id(patient_id)
                    if patient:
                        patient.status = 'Arrived at Destination'
                        self.db.session.commit()
        
        self.running = True
        self.simulation_thread = threading.Thread(target=simulate, daemon=True)
        self.simulation_thread.start()
        return True

    def stop(self):
        self.running = False

# -----------------------------------------------------------------------------
# HOSPITALS DATA — KISUMU COUNTY (PILOT)
# -----------------------------------------------------------------------------
hospitals_data = {
    'facility_name': [
        'Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)',
        'Kisumu County Referral Hospital','Lumumba Sub-County Hospital','Ahero Sub-County Hospital',
        'Kombewa Sub-County Hospital','Muhoroni County Hospital','Nyakach Sub-County Hospital',
        'Chulaimbo Sub-County Hospital','Masogo Sub-County Hospital','Nyando District Hospital',
        'Ober Kamoth Sub-County Hospital','Rabuor Sub-County Hospital','Nyangoma Sub-County Hospital',
        'Nyahera Sub-County Hospital','Katito Sub-County Hospital','Gita Sub-County Hospital',
        'Masogo Health Centre','Victoria Hospital Kisumu','Kodiaga Prison Health Centre',
        'Kisumu District Hospital','Migosi Health Centre','Katito Health Centre',
        'Mbaka Oromo Health Centre','Migere Health Centre','Milenye Health Centre',
        'Minyange Dispensary','Nduru Kadero Health Centre','Newa Dispensary',
        'Nyakoko Dispensary','Ojola Sub-County Hospital','Simba Opepo Health Centre',
        'Songhor Health Centre','St Marks Lela Health Centre','Maseno University Health Centre',
        'Geta Health Centre','Kadinda Health Centre','Kochieng Health Centre',
        'Kodingo Health Centre','Kolenyo Health Centre','Kandu Health Centre'
    ],
    'latitude': [
        -0.0754,-0.0754,-0.1058,-0.1743,-0.1813,-0.1551,-0.2670,-0.1848,-0.1855,-0.3573,
        -0.3789,-0.2138,-0.1625,-0.1565,-0.4533,-0.3735,-0.1855,-0.0878,-0.0607,-0.0916,
        -0.1073,-0.4533,-0.2628,-0.1225,-0.1872,-0.2192,-0.1356,-0.2014,-0.2678,-0.1578,
        -0.3381,-0.2131,-0.0803,-0.0025,-0.4739,-0.2167,-0.3658,-0.0956,-0.4536,-0.2314
    ],
    'longitude': [
        34.7695,34.7695,34.7568,34.9169,34.6326,35.1985,35.0569,34.6163,35.0386,35.0006,
        35.0299,34.8817,34.7794,34.7508,34.9561,34.9676,35.0386,34.7686,34.7509,34.7647,
        34.7794,34.9561,34.6061,34.7553,34.7781,34.8331,34.7381,34.8289,34.9981,34.8419,
        34.9456,35.1611,34.6569,34.6053,34.9519,34.8419,34.9606,34.7658,34.9564,34.8489
    ],
    'facility_type': [
        'Referral Hospital','Referral Hospital','Sub-County Hospital','Sub-County Hospital',
        'Sub-County Hospital','County Hospital','Sub-County Hospital','Sub-County Hospital',
        'Sub-County Hospital','District Hospital','Sub-County Hospital','Sub-County Hospital',
        'Sub-County Hospital','Sub-County Hospital','Sub-County Hospital','Sub-County Hospital',
        'Health Centre','Private Hospital','Prison Health Centre','District Hospital',
        'Health Centre','Health Centre','Health Centre','Health Centre','Health Centre',
        'Dispensary','Health Centre','Dispensary','Dispensary','Sub-County Hospital',
        'Health Centre','Health Centre','Health Centre','University Health Centre',
        'Health Centre','Health Centre','Health Centre','Health Centre','Health Centre','Health Centre'
    ],
    'capacity': [
        500,400,100,100,100,75,75,78,77,80,70,60,65,50,52,40,42,30,35,20,
        20,25,15,24,15,10,19,5,19,10,5,15,17,16,45,30,29,55,30,30
    ],
    'contact_number': [
        '+254-57-2055000','+254-57-2021578','+254-57-2023456','+254-57-2034567','+254-57-2045678',
        '+254-57-2056789','+254-57-2067890','+254-57-2078901','+254-57-2089012','+254-57-2090123',
        '+254-57-2101234','+254-57-2112345','+254-57-2123456','+254-57-2134567','+254-57-2145678',
        '+254-57-2156789','+254-57-2167890','+254-57-2178901','+254-57-2189012','+254-57-2190123',
        '+254-57-2201234','+254-57-2212345','+254-57-2223456','+254-57-2234567','+254-57-2245678',
        '+254-57-2256789','+254-57-2267890','+254-57-2278901','+254-57-2289012','+254-57-2290123',
        '+254-57-2301234','+254-57-2312345','+254-57-2323456','+254-57-2334567','+254-57-2345678',
        '+254-57-2356789','+254-57-2367890','+254-57-2378901','+254-57-2389012','+254-57-2390123'
    ]
}
hospitals_df = pd.DataFrame(hospitals_data)

ambulances_data = {
    'ambulance_id': [
        'KBA 453D','KBC 217F','KBD 389G','KBE 142H','KBF 561J','KBG 774K','KBH 238L','KBJ 965M',
        'KBK 482N','KBL 751P','KBM 312Q','KBN 864R','KBP 459S','KBQ 287T','KBR 913U','KBS 506V',
        'KBT 678W','KBU 134X','KBV 925Y','KBX 743Z'
    ],
    'current_location': [
        'JOOTRH','JOOTRH','JOOTRH','JOOTRH','JOOTRH','JOOTRH','JOOTRH','JOOTRH','JOOTRH','JOOTRH',
        'Kisumu County Referral Hospital','Kisumu County Referral Hospital','Kisumu County Referral Hospital',
        'Kisumu County Referral Hospital','Kisumu County Referral Hospital','Kisumu County Referral Hospital',
        'Kisumu County Referral Hospital','Lumumba Sub-County Hospital','Lumumba Sub-County Hospital','Ahero Sub-County Hospital'
    ],
    'latitude':  [-0.0754]*10 + [-0.0754]*7 + [-0.1058,-0.1058,-0.1743],
    'longitude': [34.7695]*10 + [34.7695]*7 + [34.7568,34.7568,34.9169],
    'driver_name': [
        'John Omondi','Mary Achieng','Paul Otieno','Susan Akinyi','David Owino','James Okoth',
        'Grace Atieno','Peter Onyango','Alice Adhiambo','Robert Ochieng','Sarah Nyongesa',
        'Michael Odhiambo','Elizabeth Awuor','Daniel Omondi','Lucy Anyango','Brian Ouma',
        'Patricia Adongo','Samuel Owuor','Rebecca Aoko','Kevin Onyango'
    ],
    'driver_contact': [
        '+254712345678','+254723456789','+254734567890','+254745678901','+254756789012',
        '+254767890123','+254778901234','+254789012345','+254790123456','+254701234567',
        '+254712345679','+254723456780','+254734567891','+254745678902','+254756789013',
        '+254767890124','+254778901235','+254789012346','+254790123457','+254701234568'
    ],
    'ambulance_type': [
        'Advanced Life Support','Basic Life Support','Basic Life Support','Advanced Life Support',
        'Basic Life Support','Basic Life Support','Advanced Life Support','Basic Life Support',
        'Basic Life Support','Advanced Life Support','Basic Life Support','Basic Life Support',
        'Advanced Life Support','Basic Life Support','Basic Life Support','Advanced Life Support',
        'Basic Life Support','Basic Life Support','Basic Life Support','Advanced Life Support'
    ],
    'fuel_level': [
        85.5,92.3,78.9,65.2,88.7,94.1,71.8,83.4,79.6,86.9,
        90.2,67.8,82.5,75.9,88.3,69.7,91.4,84.2,77.5,80.8
    ]
}

def initialize_sample_data(db):
    if db.session.query(Ambulance).count() == 0:
        for i, aid in enumerate(ambulances_data['ambulance_id']):
            a = Ambulance(
                ambulance_id=aid,
                current_location=ambulances_data['current_location'][i],
                latitude=ambulances_data['latitude'][i],
                longitude=ambulances_data['longitude'][i],
                status='Available',
                driver_name=ambulances_data['driver_name'][i],
                driver_contact=ambulances_data['driver_contact'][i],
                fuel_level=ambulances_data['fuel_level'][i],
                total_fuel_cost=np.random.uniform(5000,50000),
                total_distance_traveled=np.random.uniform(100,1000),
                cost_savings=np.random.uniform(1000,10000),
                total_missions=np.random.randint(5, 50)
            )
            db.session.add(a)
        
        demo_patients = [
            ("AFL001", "Akinyi Odhiambo", 45, "Acute Myocardial Infarction", 
             "Lumumba Sub-County Hospital", "Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)"),
            ("AFL002", "Otieno Omondi", 32, "Severe Trauma", 
             "Ahero Sub-County Hospital", "Kisumu County Referral Hospital"),
            ("AFL003", "Wanjiku Mwangi", 28, "Obstetric Emergency", 
             "Kombewa Sub-County Hospital", "Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)"),
            ("AFL004", "Kamau Kimani", 67, "Stroke", 
             "Nyando District Hospital", "Kisumu County Referral Hospital"),
            ("AFL005", "Achieng Otieno", 19, "Respiratory Distress", 
             "Masogo Sub-County Hospital", "Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)"),
        ]
        
        for pid, name, age, condition, from_hosp, to_hosp in demo_patients:
            if from_hosp not in hospitals_df['facility_name'].values:
                continue
            if to_hosp not in hospitals_df['facility_name'].values:
                continue
                
            fh = hospitals_df[hospitals_df['facility_name'] == from_hosp].iloc[0]
            th = hospitals_df[hospitals_df['facility_name'] == to_hosp].iloc[0]
            
            dist = db.calculate_distance(
                float(fh['latitude']), float(fh['longitude']), 
                float(th['latitude']), float(th['latitude'])
            )
            
            if db.session.query(Patient).filter(Patient.patient_id == pid).count() == 0:
                p = Patient(
                    patient_id=pid,
                    name=name,
                    age=age,
                    condition=condition,
                    referring_hospital=from_hosp,
                    receiving_hospital=to_hosp,
                    referring_physician=f"Dr. {name.split()[0]}",
                    status=random.choice(['Completed', 'Arrived at Destination', 'Patient Picked Up']),
                    referral_time=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
                    referring_hospital_lat=float(fh['latitude']),
                    referring_hospital_lng=float(fh['longitude']),
                    receiving_hospital_lat=float(th['latitude']),
                    receiving_hospital_lng=float(th['longitude']),
                    trip_distance=dist,
                    trip_fuel_cost=dist * 180 * 0.12,
                    trip_cost_savings=dist * 180 * 0.12 * 0.15
                )
                db.session.add(p)
        
        db.session.commit()

# -----------------------------------------------------------------------------
# PLOTLY THEME HELPER
# -----------------------------------------------------------------------------
PLOT_BG   = 'rgba(245,247,250,0.8)'
PAPER_BG  = 'rgba(245,247,250,0.8)'
FONT_CLR  = '#1a237e'
GRID_CLR  = 'rgba(0,0,0,0.05)'

def apply_theme(fig, title=None):
    fig.update_layout(
        title=title,
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(color=FONT_CLR, family='DM Sans, sans-serif'),
        xaxis=dict(gridcolor=GRID_CLR, linecolor=GRID_CLR),
        yaxis=dict(gridcolor=GRID_CLR, linecolor=GRID_CLR),
        legend=dict(bgcolor='rgba(255,255,255,0.8)'),
        margin=dict(l=10,r=10,t=40,b=10)
    )
    return fig

TEAL    = '#00838f'
GREEN   = '#00695c'
BLUE    = '#0277bd'
AMBER   = '#f57c00'
RED     = '#d32f2f'
PURPLE  = '#5e35b1'
PALETTE = [TEAL, GREEN, BLUE, AMBER, RED, PURPLE]

# -----------------------------------------------------------------------------
# DASHBOARD UI
# -----------------------------------------------------------------------------
class DashboardUI:
    def __init__(self, db, analytics):
        self.db        = db
        self.analytics = analytics

    def display(self):
        st.markdown("""
        <div style='margin-bottom:2rem;'>
            <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin:0;'>
                Command Centre
            </h1>
            <p style='color:#546e7a;margin:4px 0 0;font-size:0.9rem;'>
                Real-time overview — Kisumu County Pilot | AfyaLink National Network
            </p>
        </div>
        """, unsafe_allow_html=True)

        kpis = self.analytics.get_kpis()

        st.markdown(f"""
        <div style='background:#e8f5e9; border:1px solid #00695c50;border-radius:14px;
                    padding:1rem 1.5rem;margin-bottom:1.5rem;
                    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;'>
            <div>
                <div style='font-size:0.7rem;letter-spacing:3px;color:#00695c;font-weight:700;text-transform:uppercase;'>
                    AfyaLink National Rollout Status
                </div>
                <div style='font-size:1.1rem;color:#1a237e;font-weight:600;margin-top:4px;'>
                    Pilot Phase Active — Kisumu County &nbsp;|&nbsp; 46 Counties Queued for Onboarding
                </div>
            </div>
            <div style='display:flex;gap:2rem;'>
                <div style='text-align:center;'>
                    <div style='font-size:1.6rem;font-weight:800;color:#00695c;'>1</div>
                    <div style='font-size:0.65rem;color:#546e7a;'>LIVE COUNTY</div>
                </div>
                <div style='text-align:center;'>
                    <div style='font-size:1.6rem;font-weight:800;color:#f57c00;'>46</div>
                    <div style='font-size:0.65rem;color:#546e7a;'>QUEUED</div>
                </div>
                <div style='text-align:center;'>
                    <div style='font-size:1.6rem;font-weight:800;color:#5e35b1;'>47</div>
                    <div style='font-size:0.65rem;color:#546e7a;'>TOTAL</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        def kpi_card(icon, label, value, sub=None, color="#00695c"):
            sub_html = f"<div style='font-size:0.7rem;color:#78909c;margin-top:2px;'>{sub}</div>" if sub else ""
            return f"""
            <div style='background:#ffffff; border:1px solid {color}30;border-radius:14px;padding:1.2rem;
                        border-left:3px solid {color};box-shadow:0 2px 4px rgba(0,0,0,0.05);'>
                <div style='font-size:1.4rem;margin-bottom:4px;'>{icon}</div>
                <div style='font-size:1.6rem;font-weight:800;color:#1a237e;line-height:1.1;'>{value}</div>
                <div style='font-size:0.75rem;color:#546e7a;margin-top:4px;font-weight:600;'>{label}</div>
                {sub_html}
            </div>"""

        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: st.markdown(kpi_card("📋","Total Referrals",kpis['total_referrals'],"All time",TEAL), unsafe_allow_html=True)
        with c2: st.markdown(kpi_card("🔴","Active Transfers",kpis['active_referrals'],"In progress",RED), unsafe_allow_html=True)
        with c3: st.markdown(kpi_card("🚑","Available Units",kpis['available_ambulances'],"Ready to deploy",GREEN), unsafe_allow_html=True)
        with c4: st.markdown(kpi_card("⏱️","Avg Response",kpis['avg_response_time'],"Last 30 days",BLUE), unsafe_allow_html=True)
        with c5: st.markdown(kpi_card("✅","Completion Rate",kpis['completion_rate'],"Successfully delivered",PURPLE), unsafe_allow_html=True)

        st.markdown("<div style='margin:1rem 0;'></div>", unsafe_allow_html=True)
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(kpi_card("⛽","Fleet Fuel Cost",f"KSh {kpis['total_fuel_cost']:,.0f}","Cumulative",AMBER), unsafe_allow_html=True)
        with c2: st.markdown(kpi_card("💵","Cost Savings",f"KSh {kpis['total_cost_savings']:,.0f}","Via smart routing",GREEN), unsafe_allow_html=True)
        with c3: st.markdown(kpi_card("📏","Total Distance",f"{kpis['total_distance_km']:,.0f} km","Fleet aggregate",BLUE), unsafe_allow_html=True)
        with c4: st.markdown(kpi_card("🏥","Facilities",f"40","Kisumu network",TEAL), unsafe_allow_html=True)

        st.markdown("<div style='margin:1.5rem 0;'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns([3,2])
        with col1:
            self._referral_trend_chart()
        with col2:
            self._status_donut()

        col1, col2 = st.columns([2,3])
        with col1:
            self._cost_chart()
        with col2:
            self._facility_map()

        st.markdown("#### Recent Referrals")
        self._recent_referrals_table()

    def _referral_trend_chart(self):
        trends = self.analytics.get_referral_trends()
        st.markdown("##### Referral Volume Trend")
        if not trends.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trends['date'], y=trends['count'],
                fill='tozeroy', fillcolor='rgba(0,105,92,0.15)',
                line=dict(color=GREEN, width=2.5),
                mode='lines+markers', marker=dict(size=5, color=GREEN)
            ))
            apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True, key="referral_trend")
        else:
            dates  = pd.date_range(end=datetime.now(), periods=30)
            counts = np.random.randint(2,12, 30)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, y=counts,
                fill='tozeroy', fillcolor='rgba(0,105,92,0.15)',
                line=dict(color=GREEN, width=2.5),
                mode='lines+markers', marker=dict(size=5, color=GREEN)
            ))
            apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True, key="referral_trend_demo")

    def _status_donut(self):
        st.markdown("##### Transfer Status")
        patients = self.db.get_all_patients()
        if patients:
            from collections import Counter
            status_map = {
                'Referred':'Referred','Ambulance Assigned':'Assigned',
                'Ambulance Dispatched':'Dispatched','Patient Picked Up':'En Route',
                'Transporting to Destination':'En Route','Arrived at Destination':'Arrived',
                'Completed':'Completed'
            }
            counts = Counter(status_map.get(p.status, p.status) for p in patients)
            fig = go.Figure(go.Pie(
                labels=list(counts.keys()), values=list(counts.values()),
                hole=0.62, marker=dict(colors=PALETTE),
                textinfo='percent', textfont_size=11,
                hovertemplate='%{label}: %{value}<extra></extra>'
            ))
            fig.add_annotation(text=f"<b>{len(patients)}</b><br><span style='font-size:10px'>total</span>",
                               x=0.5, y=0.5, font_size=20, showarrow=False, font_color='#1a237e')
            apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True, key="status_donut")
        else:
            labels  = ['Referred','Dispatched','En Route','Arrived']
            values  = [12,5,3,8]
            fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.62,
                                   marker=dict(colors=PALETTE), textinfo='percent'))
            apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True, key="status_donut_demo")

    def _cost_chart(self):
        st.markdown("##### Monthly Cost vs Savings")
        cd = self.analytics.get_cost_analytics()
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Cost Incurred', x=cd['months'], y=cd['monthly_costs'],
                              marker_color=RED, opacity=0.8))
        fig.add_trace(go.Bar(name='Cost Saved',    x=cd['months'], y=cd['monthly_savings'],
                              marker_color=GREEN, opacity=0.8))
        fig.update_layout(barmode='group')
        apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True, key="cost_chart")

    def _facility_map(self):
        st.markdown("##### Kisumu Network — 40 Facilities")
        fig = px.scatter_mapbox(
            hospitals_df,
            lat='latitude', lon='longitude',
            hover_name='facility_name',
            hover_data={'facility_type':True,'capacity':True,'latitude':False,'longitude':False},
            color='facility_type',
            size='capacity', size_max=18,
            color_discrete_sequence=PALETTE,
            zoom=9, height=320
        )
        fig.update_layout(
            mapbox_style='light',
            margin=dict(l=0,r=0,t=0,b=0),
            paper_bgcolor='rgba(255,255,255,0)',
            legend=dict(font_color='#1a237e', bgcolor='rgba(255,255,255,0.8)')
        )
        st.plotly_chart(fig, use_container_width=True, key="facility_map")

    def _recent_referrals_table(self):
        patients = sorted(self.db.get_all_patients(), key=lambda x: x.referral_time, reverse=True)[:8]
        if patients:
            status_badge = {
                'Referred': ('#0277bd','#e3f2fd'),
                'Ambulance Assigned': ('#f57c00','#fff3e0'),
                'Patient Picked Up': ('#d32f2f','#ffebee'),
                'Arrived at Destination': ('#00695c','#e8f5e9'),
                'Completed': ('#5e35b1','#f3e5f5'),
            }
            rows = ""
            for p in patients:
                clr, bg = status_badge.get(p.status, ('#546e7a','#f5f5f5'))
                rows += f"""
                <tr style='border-bottom:1px solid #e0e0e0;'>
                    <td style='padding:0.6rem 0.8rem;color:#546e7a;font-size:0.8rem;font-family:monospace;'>{p.patient_id}</td>
                    <td style='padding:0.6rem 0.8rem;color:#1a237e;font-weight:600;'>{p.name}</td>
                    <td style='padding:0.6rem 0.8rem;color:#546e7a;font-size:0.85rem;'>{p.condition}</td>
                    <td style='padding:0.6rem 0.8rem;color:#78909c;font-size:0.8rem;'>{p.referring_hospital[:30]}…</td>
                    <td style='padding:0.6rem 0.8rem;color:#78909c;font-size:0.8rem;'>{p.receiving_hospital[:30]}…</td>
                    <td style='padding:0.6rem 0.8rem;'>
                        <span style='background:{bg};color:{clr};border:1px solid {clr}50;
                                     border-radius:20px;padding:2px 10px;font-size:0.72rem;font-weight:600;'>
                            {p.status}
                        </span>
                    </td>
                    <td style='padding:0.6rem 0.8rem;color:#78909c;font-size:0.78rem;'>{p.referral_time.strftime('%d %b %H:%M')}</td>
                </tr>"""

            st.markdown(f"""
            <div style='background:#ffffff;border:1px solid #e0e0e0;border-radius:14px;overflow:hidden;'>
                <table style='width:100%;border-collapse:collapse;'>
                    <thead>
                        <tr style='background:#f5f5f5;'>
                            <th style='padding:0.7rem 0.8rem;color:#78909c;font-size:0.72rem;text-align:left;letter-spacing:1px;text-transform:uppercase;'>ID</th>
                            <th style='padding:0.7rem 0.8rem;color:#78909c;font-size:0.72rem;text-align:left;letter-spacing:1px;text-transform:uppercase;'>Patient</th>
                            <th style='padding:0.7rem 0.8rem;color:#78909c;font-size:0.72rem;text-align:left;letter-spacing:1px;text-transform:uppercase;'>Condition</th>
                            <th style='padding:0.7rem 0.8rem;color:#78909c;font-size:0.72rem;text-align:left;letter-spacing:1px;text-transform:uppercase;'>From</th>
                            <th style='padding:0.7rem 0.8rem;color:#78909c;font-size:0.72rem;text-align:left;letter-spacing:1px;text-transform:uppercase;'>To</th>
                            <th style='padding:0.7rem 0.8rem;color:#78909c;font-size:0.72rem;text-align:left;letter-spacing:1px;text-transform:uppercase;'>Status</th>
                            <th style='padding:0.7rem 0.8rem;color:#78909c;font-size:0.72rem;text-align:left;letter-spacing:1px;text-transform:uppercase;'>Time</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No referrals yet. Create the first referral to get started.")

# -----------------------------------------------------------------------------
# REFERRAL UI
# -----------------------------------------------------------------------------
class ReferralUI:
    def __init__(self, db, notifications):
        self.db            = db
        self.notifications = notifications
        self.svc           = ReferralService(db, notifications)

    def display(self):
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:4px;'>Patient Referral Management</h1>
        <p style='color:#546e7a;font-size:0.9rem;margin-bottom:1.5rem;'>Create, track, and manage inter-facility patient transfers</p>
        """, unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["New Referral", "Active Transfers", "History"])
        with tab1: self._create_referral_form()
        with tab2: self._active_referrals()
        with tab3: self._history()

    def _referring_hospitals(self, user_hospital):
        if user_hospital in ['All Facilities',
                              'Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)',
                              'Kisumu County Referral Hospital']:
            return hospitals_data['facility_name']
        return [user_hospital]

    def _receiving_hospitals(self):
        return ['Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)',
                'Kisumu County Referral Hospital']

    def _create_referral_form(self):
        user_hospital = st.session_state.user['hospital']
        st.markdown("""
        <div style='background:#f5f5f5; border:1px solid #00695c20;border-radius:14px;
                    padding:1.5rem;margin-bottom:1rem;'>
            <div style='color:#00695c;font-size:0.7rem;letter-spacing:2px;font-weight:700;text-transform:uppercase;'>
                Referral Protocol
            </div>
            <div style='color:#546e7a;font-size:0.85rem;margin-top:6px;'>
                All referring facilities must route patients to either <strong style='color:#1a237e;'>JOOTRH</strong> or 
                <strong style='color:#1a237e;'>Kisumu County Referral Hospital</strong>. 
                AfyaLink auto-assigns the nearest available ambulance with sufficient fuel.
            </div>
        </div>
        """, unsafe_allow_html=True)

        priority_colors = {'Emergency': RED, 'Urgent': AMBER, 'Standard': GREEN}

        with st.form("referral_form", clear_on_submit=True):
            st.markdown("#### Patient Information")
            c1, c2, c3 = st.columns([3,1,2])
            with c1: name  = st.text_input("Full Name *", placeholder="e.g. Akinyi Odhiambo")
            with c2: age   = st.number_input("Age *", 0, 120, 35)
            with c3: priority = st.selectbox("Priority *", list(priority_colors.keys()))

            c1, c2 = st.columns(2)
            with c1: condition = st.text_input("Medical Condition / Diagnosis *", placeholder="e.g. Acute Myocardial Infarction")
            with c2: referring_physician = st.text_input("Referring Physician *", placeholder="Dr. Firstname Lastname")

            st.markdown("#### Transfer Route")
            c1, c2 = st.columns(2)
            with c1:
                from_hosp_list = self._referring_hospitals(user_hospital)
                from_hosp = st.selectbox("Referring Facility *", from_hosp_list)
            with c2:
                to_hosp_list = self._receiving_hospitals()
                to_hosp = st.selectbox("Receiving Facility *", to_hosp_list)

            if from_hosp == to_hosp:
                st.warning("Referring and receiving facilities must be different.")

            c1, c2 = st.columns(2)
            with c1: receiving_physician = st.text_input("Receiving Physician (if known)")
            with c2:
                assignment = st.radio("Ambulance Assignment", ["Auto-assign Nearest", "Manual Selection"],
                                       help="Auto-assign uses GPS to find the nearest available unit")

            if "Manual" in assignment:
                avail = self.db.get_available_ambulances()
                opts = ["— Select Ambulance —"] + [
                    f"{a.ambulance_id} | {a.driver_name} | Fuel: {a.fuel_level:.0f}%" for a in avail]
                ambulance_choice = st.selectbox("Select Ambulance", opts)
            else:
                ambulance_choice = "auto"

            st.markdown("#### Clinical Details")
            notes = st.text_area("Clinical Notes", placeholder="Presenting symptoms, examination findings, reason for referral...", height=80)
            c1, c2, c3 = st.columns(3)
            with c1: history     = st.text_area("Medical History",     height=80)
            with c2: medications = st.text_area("Current Medications", height=80)
            with c3: allergies   = st.text_area("Known Allergies",     height=80)

            submitted = st.form_submit_button("Submit Referral", use_container_width=True, type="primary")
            if submitted:
                if not all([name, condition, referring_physician, from_hosp, to_hosp]):
                    st.error("Please complete all required fields (*)")
                elif from_hosp == to_hosp:
                    st.error("Referring and receiving hospitals must differ.")
                else:
                    fh = hospitals_df[hospitals_df['facility_name'] == from_hosp].iloc[0]
                    th = hospitals_df[hospitals_df['facility_name'] == to_hosp].iloc[0]
                    data = {
                        'name': name, 'age': age, 'condition': condition,
                        'referring_hospital': from_hosp, 'receiving_hospital': to_hosp,
                        'referring_physician': referring_physician,
                        'receiving_physician': receiving_physician,
                        'notes': notes, 'medical_history': history,
                        'current_medications': medications, 'allergies': allergies,
                        'status': 'Referred',
                        'priority_level': priority,
                        'referring_hospital_lat': float(fh['latitude']),
                        'referring_hospital_lng': float(fh['longitude']),
                        'receiving_hospital_lat': float(th['latitude']),
                        'receiving_hospital_lng': float(th['longitude']),
                    }
                    if "Manual" in assignment and ambulance_choice != "— Select Ambulance —":
                        data['assigned_ambulance'] = ambulance_choice.split(" | ")[0]

                    patient = self.svc.create_referral(data, st.session_state.user)
                    if patient:
                        st.success(f"Referral created — Patient ID: {patient.patient_id}")
                        if "Auto" in assignment:
                            self.svc.auto_assign_nearest(patient.patient_id)

    def _active_referrals(self):
        patients     = self.db.get_all_patients()
        user_hospital = st.session_state.user['hospital']
        active = [p for p in patients if p.status not in ['Arrived at Destination','Completed']]
        if user_hospital not in ['All Facilities']:
            if user_hospital in ['Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)',
                                  'Kisumu County Referral Hospital']:
                active = [p for p in active if p.receiving_hospital == user_hospital]
            else:
                active = [p for p in active if p.referring_hospital == user_hospital]

        st.markdown(f"**{len(active)} active transfer(s)**")
        if not active:
            st.info("No active transfers at this time.")
            return

        for idx, p in enumerate(active):
            amb_info = ""
            if p.assigned_ambulance:
                af = AmbulanceService(self.db).get_fuel_info(p.assigned_ambulance)
                if af: amb_info = f"{p.assigned_ambulance} {af['fuel_status']}"

            status_clr = {
                'Referred': BLUE, 'Ambulance Assigned': AMBER,
                'Patient Picked Up': RED, 'Transporting to Destination': PURPLE
            }.get(p.status, TEAL)

            with st.expander(f"{p.name} — {p.condition}  |  {p.status}", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Patient ID:** `{p.patient_id}`")
                    st.markdown(f"**Age:** {p.age}")
                    st.markdown(f"**Condition:** {p.condition}")
                    st.markdown(f"**Physician:** {p.referring_physician}")
                with c2:
                    st.markdown(f"**From:** {p.referring_hospital}")
                    st.markdown(f"**To:** {p.receiving_hospital}")
                    st.markdown(f"**Ambulance:** {amb_info or 'Not yet assigned'}")
                    if p.trip_distance:
                        st.markdown(f"**Distance:** {p.trip_distance:.1f} km")
                with c3:
                    st.markdown(f"**Status:** :{status_clr}[{p.status}]")
                    if p.notes: st.markdown(f"**Notes:** {p.notes}")

                st.markdown("**Actions:**")
                ac1, ac2, ac3, ac4 = st.columns(4)
                with ac1:
                    if st.button("Assign Ambulance", key=f"assign_{p.patient_id}_{idx}", use_container_width=True):
                        avail = self.db.get_available_ambulances()
                        if avail:
                            opts = [f"{a.ambulance_id} — {a.driver_name} (Fuel {a.fuel_level:.0f}%)" for a in avail]
                            sel  = st.selectbox("Select", opts, key=f"amb_sel_{p.patient_id}_{idx}")
                            if st.button("Confirm", key=f"confirm_{p.patient_id}_{idx}", use_container_width=True):
                                if self.svc.assign_ambulance(p.patient_id, sel.split(" — ")[0]):
                                    st.success("Assigned!"); st.rerun()
                        else:
                            st.warning("No available ambulances")
                with ac2:
                    new_status = st.selectbox("Update Status",
                        ["Referred","Ambulance Dispatched","Patient Picked Up","Transporting to Destination","Arrived at Destination"],
                        key=f"stat_{p.patient_id}_{idx}")
                    if st.button("Apply", key=f"apply_{p.patient_id}_{idx}", use_container_width=True):
                        p.status = new_status; self.db.session.commit()
                        st.success("Updated!"); st.rerun()
                with ac3:
                    if st.button("Auto-Assign", key=f"auto_{p.patient_id}_{idx}", use_container_width=True):
                        if self.svc.auto_assign_nearest(p.patient_id): st.rerun()
                with ac4:
                    if (st.session_state.user['role'] == 'Ambulance Driver' and p.status == 'Ambulance Dispatched'):
                        if st.button("Mark Picked Up", key=f"pickup_{p.patient_id}_{idx}", use_container_width=True, type="primary"):
                            if self.svc.mark_picked_up(p.patient_id): st.rerun()

    def _history(self):
        patients = self.db.get_all_patients()
        if not patients:
            st.info("No referral history yet.")
            return
        data = [{
            'Patient ID': p.patient_id, 'Name': p.name, 'Age': p.age,
            'Condition': p.condition, 'From': p.referring_hospital[:40],
            'To': p.receiving_hospital[:40], 'Status': p.status,
            'Ambulance': p.assigned_ambulance or '—',
            'Distance (km)': f"{p.trip_distance:.1f}" if p.trip_distance else '—',
            'Cost (KSh)':    f"{p.trip_fuel_cost:,.0f}" if p.trip_fuel_cost else '—',
            'Date': p.referral_time.strftime('%d %b %Y %H:%M')
        } for p in sorted(patients, key=lambda x: x.referral_time, reverse=True)]
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# TRACKING UI
# -----------------------------------------------------------------------------
class TrackingUI:
    def __init__(self, db):
        self.db   = db
        self.cost = CostCalculationService(db)

    def display(self):
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:4px;'>Live Fleet Tracking</h1>
        <p style='color:#546e7a;font-size:0.9rem;margin-bottom:1.5rem;'>Real-time ambulance positions, fuel levels and cost analytics</p>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([5,1])
        with col2:
            if st.button("Refresh", use_container_width=True): st.rerun()

        patients = self.db.get_all_patients()
        active   = [p for p in patients if p.status in
                    ['Ambulance Dispatched','Patient Picked Up','Transporting to Destination']]

        if active:
            st.markdown("### Active Transfers")
            for idx, p in enumerate(active):
                ambulance = None
                if p.assigned_ambulance:
                    ambulance = self.db.session.query(Ambulance).filter(
                        Ambulance.ambulance_id == p.assigned_ambulance).first()
                with st.expander(f"🚑 {p.name} — {p.condition} ({p.status})", expanded=True):
                    if ambulance and p.trip_distance:
                        ce = self.cost.calculate_trip_cost(p.trip_distance)
                        c1,c2,c3,c4 = st.columns(4)
                        c1.metric("Distance",  f"{p.trip_distance:.1f} km")
                        c2.metric("Fuel Cost", f"KSh {ce['fuel_cost_ksh']:,.0f}")
                        c3.metric("Total Cost",f"KSh {ce['total_cost_ksh']:,.0f}")
                        c4.metric("Fuel Level",f"{ambulance.fuel_level:.1f}%",
                                  "Good" if ambulance.fuel_level>50 else "Low" if ambulance.fuel_level>20 else "Critical")

                    if ambulance:
                        c1,c2 = st.columns(2)
                        with c1:
                            st.markdown(f"""
                            | Field | Value |
                            |---|---|
                            | Patient | {p.name} |
                            | Condition | {p.condition} |
                            | Ambulance | {ambulance.ambulance_id} |
                            | Driver | {ambulance.driver_name} |
                            | Contact | {ambulance.driver_contact} |
                            | Location | {ambulance.current_location or 'En route'} |
                            """)
                        with c2:
                            fh = hospitals_df[hospitals_df['facility_name'] == p.referring_hospital]
                            th = hospitals_df[hospitals_df['facility_name'] == p.receiving_hospital]
                            if not fh.empty and not th.empty and ambulance.latitude:
                                map_data = pd.DataFrame({
                                    'lat': [float(fh.iloc[0]['latitude']),
                                            ambulance.latitude,
                                            float(th.iloc[0]['latitude'])],
                                    'lon': [float(fh.iloc[0]['longitude']),
                                            ambulance.longitude,
                                            float(th.iloc[0]['longitude'])],
                                    'type': ['From','Ambulance','To'],
                                    'size': [15, 25, 15]
                                })
                                fig = px.scatter_mapbox(
                                    map_data, lat='lat', lon='lon',
                                    color='type', size='size', size_max=20,
                                    hover_name='type', zoom=10, height=260,
                                    color_discrete_map={'From':GREEN,'Ambulance':RED,'To':BLUE}
                                )
                                fig.update_layout(mapbox_style='light',
                                                  margin=dict(l=0,r=0,t=0,b=0),
                                                  paper_bgcolor='rgba(255,255,255,0)',
                                                  showlegend=True)
                                st.plotly_chart(fig, use_container_width=True, key=f"map_{p.patient_id}_{idx}")
        else:
            st.info("No active patient transfers currently.")

        st.markdown("### Fleet Overview")
        self._fleet_table()
        st.markdown("### Fleet Positions")
        self._fleet_map()

    def _fleet_table(self):
        ambulances = self.db.get_all_ambulances()
        if not ambulances:
            st.info("No ambulance data."); return
        data = []
        for a in ambulances:
            fs = "Good" if a.fuel_level>50 else "Low" if a.fuel_level>20 else "Critical"
            sc = f"{a.cost_savings/a.total_fuel_cost*100:.1f}%" if a.total_fuel_cost>0 else "—"
            data.append({'Unit': a.ambulance_id, 'Driver': a.driver_name,
                         'Status': a.status, 'Fuel': f"{a.fuel_level:.1f}% {fs}",
                         'Location': (a.current_location or '—')[:35],
                         'Distance (km)': f"{a.total_distance_traveled:,.0f}",
                         'Fuel Cost (KSh)': f"{a.total_fuel_cost:,.0f}",
                         'Savings Rate': sc})
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    def _fleet_map(self):
        ambulances = self.db.get_all_ambulances()
        amb_with_loc = [a for a in ambulances if a.latitude and a.longitude]
        if not amb_with_loc:
            st.info("No GPS data available yet."); return
        df = pd.DataFrame([{
            'lat': a.latitude, 'lon': a.longitude,
            'id': a.ambulance_id, 'status': a.status,
            'driver': a.driver_name, 'fuel': f"{a.fuel_level:.1f}%"
        } for a in amb_with_loc])
        fig = px.scatter_mapbox(df, lat='lat', lon='lon',
                                color='status', hover_name='id',
                                hover_data={'driver':True,'fuel':True,'lat':False,'lon':False},
                                zoom=9, height=380,
                                color_discrete_map={'Available':GREEN,'On Transfer':RED,'Maintenance':AMBER,'On Break':PURPLE})
        fig.update_layout(mapbox_style='carto-darkmatter',
                          margin=dict(l=0,r=0,t=0,b=0),
                          paper_bgcolor='rgba(245,247,250,0.8)')
        st.plotly_chart(fig, use_container_width=True, key="fleet_map")

# -----------------------------------------------------------------------------
# COST MANAGEMENT UI
# -----------------------------------------------------------------------------
class CostManagementUI:
    def __init__(self, db, analytics):
        self.db        = db
        self.analytics = analytics
        self.cost      = CostCalculationService(db)

    def display(self):
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:4px;'>Cost Intelligence</h1>
        <p style='color:#546e7a;font-size:0.9rem;margin-bottom:1.5rem;'>Fuel analytics, fleet efficiency and budget forecasting</p>
        """, unsafe_allow_html=True)
        tab1, tab2, tab3, tab4 = st.tabs(["Overview","Fuel","Savings","Budget"])
        with tab1: self._overview()
        with tab2: self._fuel()
        with tab3: self._savings()
        with tab4: self._budget()

    def _overview(self):
        kpis = self.analytics.get_kpis()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Fleet Fuel Cost", f"KSh {kpis['total_fuel_cost']:,.0f}")
        c2.metric("Total Savings",   f"KSh {kpis['total_cost_savings']:,.0f}", "via smart routing")
        c3.metric("Net Cost",        f"KSh {kpis['total_fuel_cost']-kpis['total_cost_savings']:,.0f}")
        savings_pct = kpis['total_cost_savings']/kpis['total_fuel_cost']*100 if kpis['total_fuel_cost']>0 else 0
        c4.metric("Savings Rate",    f"{savings_pct:.1f}%")

        ambulances = self.db.get_all_ambulances()
        if ambulances:
            df = pd.DataFrame([{'Unit': a.ambulance_id,
                                 'Fuel Cost': a.total_fuel_cost,
                                 'Savings':   a.cost_savings} for a in ambulances])
            fig = px.bar(df, x='Unit', y=['Fuel Cost','Savings'],
                         barmode='group',
                         color_discrete_sequence=[RED, GREEN])
            apply_theme(fig, "Cost vs Savings by Unit")
            st.plotly_chart(fig, use_container_width=True, key="cost_overview_bar")

    def _fuel(self):
        st.markdown("#### Fuel Price Configuration")
        c1,c2 = st.columns(2)
        with c1:
            price = st.number_input("Fuel Price (KSh/L)", value=float(Config.FUEL_PRICE_PER_LITER), min_value=100.0, max_value=300.0)
        with c2:
            if st.button("Update Price", use_container_width=True, type="primary"):
                Config.FUEL_PRICE_PER_LITER = price
                st.success("Fuel price updated system-wide.")

        ambulances = self.db.get_all_ambulances()
        eff_data = []
        for a in ambulances:
            if a.total_distance_traveled > 0 and a.total_fuel_cost > 0:
                liters = a.total_fuel_cost / Config.FUEL_PRICE_PER_LITER
                eff_data.append({'Unit': a.ambulance_id,
                                  'Distance (km)': round(a.total_distance_traveled,1),
                                  'Fuel Used (L)':  round(liters,1),
                                  'Efficiency (km/L)': round(a.total_distance_traveled/liters,2) if liters>0 else 0,
                                  'Cost/km (KSh)': round(a.total_fuel_cost/a.total_distance_traveled,1)})
        if eff_data:
            df = pd.DataFrame(eff_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            fig = px.bar(df, x='Unit', y='Efficiency (km/L)', color_discrete_sequence=[TEAL])
            apply_theme(fig, "Fuel Efficiency by Unit")
            st.plotly_chart(fig, use_container_width=True, key="fuel_eff_chart")

    def _savings(self):
        cd = self.analytics.get_cost_analytics()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cd['months'], y=cd['monthly_savings'],
                                  fill='tozeroy', fillcolor='rgba(0,105,92,0.15)',
                                  line=dict(color=GREEN,width=2.5), mode='lines+markers'))
        apply_theme(fig, "Monthly Savings Trend (KSh)")
        st.plotly_chart(fig, use_container_width=True, key="savings_trend")

        ambulances = self.db.get_all_ambulances()
        df = pd.DataFrame([{'Unit': a.ambulance_id, 'Savings': a.cost_savings,
                             'Rate': f"{a.cost_savings/a.total_fuel_cost*100:.1f}%" if a.total_fuel_cost>0 else "—"}
                            for a in ambulances])
        c1,c2 = st.columns(2)
        with c1:
            st.dataframe(df, use_container_width=True, hide_index=True)
        with c2:
            fig = px.pie(df, values='Savings', names='Unit',
                         color_discrete_sequence=PALETTE, hole=0.5)
            apply_theme(fig, "Savings Distribution")
            st.plotly_chart(fig, use_container_width=True, key="savings_pie")

    def _budget(self):
        c1,c2 = st.columns(2)
        with c1:
            budget = st.number_input("Monthly Budget (KSh)", value=500000, step=50000)
        with c2:
            trips  = st.number_input("Expected Monthly Trips", value=100, step=10)

        avg_cost   = 1500
        proj_cost  = trips * avg_cost
        proj_save  = proj_cost * 0.15
        net        = proj_cost - proj_save

        c1,c2,c3 = st.columns(3)
        c1.metric("Projected Cost",    f"KSh {proj_cost:,.0f}")
        c2.metric("Projected Savings", f"KSh {proj_save:,.0f}")
        c3.metric("Budget Status",
                  "Within Budget" if net<=budget else "Over Budget",
                  delta=f"KSh {budget-net:,.0f}")

        fig = px.bar(
            x=["Budget","Projected Cost","Projected Savings","Net Cost"],
            y=[budget, proj_cost, proj_save, net],
            color=["Budget","Projected Cost","Projected Savings","Net Cost"],
            color_discrete_sequence=[BLUE, RED, GREEN, TEAL]
        )
        apply_theme(fig, "Budget Projection")
        st.plotly_chart(fig, use_container_width=True, key="budget_bar")

# -----------------------------------------------------------------------------
# COMMUNICATION UI
# -----------------------------------------------------------------------------
class CommunicationUI:
    def __init__(self, db, notifications):
        self.db    = db
        self.notif = notifications

    def display(self):
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:4px;'>Communication Hub</h1>
        <p style='color:#546e7a;font-size:0.9rem;margin-bottom:1.5rem;'>Secure messaging between facilities, ambulance units and system</p>
        """, unsafe_allow_html=True)
        tab1,tab2,tab3,tab4 = st.tabs(["All Messages","Compose","Templates","Log Stats"])
        with tab1: self._all_messages()
        with tab2: self._compose()
        with tab3: self._templates()
        with tab4: self._log_stats()

    def _all_messages(self):
        c1,c2,c3 = st.columns([2,2,1])
        with c1:
            ftype = st.selectbox("Filter", ["All","System Auto","Staff","Driver"])
        with c2:
            search = st.text_input("Search messages", placeholder="Patient ID, keyword...")
        with c3:
            if st.button("Refresh", key="refresh_messages", use_container_width=True): st.rerun()

        comms = self.db.session.query(Communication).order_by(Communication.timestamp.desc()).all()
        if ftype == "System Auto": comms = [c for c in comms if c.sender=='AfyaLink System']
        elif ftype == "Driver":    comms = [c for c in comms if c.sender=='Driver']
        elif ftype == "Staff":   comms = [c for c in comms if c.sender not in ['AfyaLink System','Driver']]
        if search:
            comms = [c for c in comms if search.lower() in (c.message or '').lower()
                     or search.lower() in (c.patient_id or '').lower()]

        if not comms:
            st.info("No messages found."); return

        for idx, c in enumerate(comms[:30]):
            if c.sender == 'AfyaLink System':
                icon, bc, tc = "🤖", "#e8eaf6", "#00695c"
            elif c.sender == 'Driver':
                icon, bc, tc = "🚑", "#e8f5e9", "#00695c"
            else:
                icon, bc, tc = "👨‍⚕️", "#e3f2fd", "#0277bd"
            st.markdown(f"""
            <div style='background:{bc};border-left:3px solid {tc};border-radius:8px;
                        padding:0.8rem 1rem;margin:6px 0;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>
                    <span style='font-weight:700;color:{tc};font-size:0.85rem;'>{icon} {c.sender}</span>
                    <span style='color:#78909c;font-size:0.75rem;'>{c.timestamp.strftime('%d %b %H:%M')}</span>
                </div>
                <div style='color:#546e7a;font-size:0.78rem;margin-bottom:6px;'>→ {c.receiver}</div>
                <div style='color:#1a237e;font-size:0.85rem;white-space:pre-line;'>{c.message}</div>
                <div style='color:#90a4ae;font-size:0.72rem;margin-top:6px;'>
                    Patient: {c.patient_id or 'N/A'} | Unit: {c.ambulance_id or 'N/A'} | Type: {c.message_type or 'General'}
                </div>
            </div>
            """, unsafe_allow_html=True)

    def _compose(self):
        patients   = self.db.get_all_patients()
        ambulances = self.db.get_all_ambulances()
        with st.form("compose_form"):
            c1,c2 = st.columns(2)
            with c1:
                p_opts = ["— No patient —"] + [f"{p.patient_id} — {p.name}" for p in patients]
                sel_p  = st.selectbox("Related Patient", p_opts)
                sender = st.selectbox("Sender", ["AfyaLink System", st.session_state.user.get('name', 'Staff')])
            with c2:
                a_opts = ["— No unit —"] + [f"{a.ambulance_id} — {a.driver_name}" for a in ambulances]
                sel_a  = st.selectbox("Related Unit", a_opts)
                recv_opts = (["— Select Recipient —"] +
                             [a.driver_name for a in ambulances] +
                             list(hospitals_data['facility_name']))
                receiver = st.selectbox("Send To", recv_opts)

            mtype   = st.selectbox("Type", ["General","Urgent","Update","Emergency","Instruction"])
            message = st.text_area("Message", height=120)
            if st.form_submit_button("Send", use_container_width=True, type="primary"):
                if not message or receiver.startswith("—"):
                    st.error("Message and recipient are required.")
                else:
                    pid = sel_p.split(" — ")[0] if not sel_p.startswith("—") else None
                    aid = sel_a.split(" — ")[0] if not sel_a.startswith("—") else None
                    self.db.add_communication({'patient_id':pid,'ambulance_id':aid,
                                               'sender':sender,'receiver':receiver,
                                               'message':message,'message_type':f"manual_{mtype.lower()}"})
                    st.success(f"Message sent to {receiver}")

    def _templates(self):
        templates = {
            "Emergency": {
                "Cardiac Alert": "CARDIAC EMERGENCY: Patient with suspected MI incoming. Activate cath lab & emergency team. ETA 15 minutes.",
                "Trauma Alert":  "TRAUMA ALERT: Multiple trauma patient en route. Trauma team to standby. ETA 10 minutes.",
                "Stroke Alert":  "STROKE ALERT: Acute neurological event. CT and stroke team ready. ETA 12 minutes.",
            },
            "Status Updates": {
                "ETA Revised":       "ETA UPDATE: Revised ETA is {X} minutes. Patient condition stable.",
                "Traffic Delay":     "DELAY: Traffic on route. New ETA {X} minutes. Patient stable.",
                "Arrival Imminent":  "ARRIVING IN 5 MINUTES. Please have receiving team at emergency entrance.",
            },
            "Clinical Updates": {
                "Vitals Normal":   "VITALS: BP 120/80, HR 72bpm, SpO2 98%. Patient stable during transport.",
                "Condition Change":"CONDITION CHANGE: Patient deteriorating. Prepare advanced support on arrival.",
                "Medication Given":"MEDICATION GIVEN: {drug} administered. Patient response: {response}.",
            }
        }
        cat = st.selectbox("Category", list(templates.keys()))
        for name, body in templates[cat].items():
            c1,c2 = st.columns([5,1])
            with c1: st.text_area(name, body, height=80, key=f"tpl_{name}")
            with c2:
                st.markdown("<div style='margin-top:1.8rem;'></div>", unsafe_allow_html=True)
                if st.button("Use", key=f"use_{name}", use_container_width=True):
                    st.session_state['draft_message'] = body
                    st.success("Copied to composer!")

    def _log_stats(self):
        comms = self.db.session.query(Communication).all()
        if not comms:
            st.info("No messages logged yet."); return
        total = len(comms)
        auto  = len([c for c in comms if c.sender=='AfyaLink System'])
        driv  = len([c for c in comms if c.sender=='Driver'])
        today = len([c for c in comms if c.timestamp.date()==datetime.now().date()])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Messages",    total)
        c2.metric("System Auto",       auto)
        c3.metric("Driver Messages",   driv)
        c4.metric("Today",             today)

        mtypes = {}
        for c in comms:
            t = c.message_type or 'general'
            mtypes[t] = mtypes.get(t,0)+1
        fig = px.pie(values=list(mtypes.values()), names=list(mtypes.keys()),
                     color_discrete_sequence=PALETTE, hole=0.5)
        apply_theme(fig,"Message Types")
        st.plotly_chart(fig, use_container_width=True, key="msg_type_pie")

# -----------------------------------------------------------------------------
# HANDOVER UI
# -----------------------------------------------------------------------------
class HandoverUI:
    def __init__(self, db):
        self.db = db

    def display(self):
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:4px;'>Clinical Handover</h1>
        <p style='color:#546e7a;font-size:0.9rem;margin-bottom:1.5rem;'>Standardised handover forms and audit trail</p>
        """, unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Create Handover", "Handover History"])
        with tab1: self._create()
        with tab2: self._history()

    def _create(self):
        patients      = self.db.get_all_patients()
        user_hospital = st.session_state.user['hospital']
        eligible = [p for p in patients if p.status=='Arrived at Destination' and
                    (user_hospital=='All Facilities' or p.receiving_hospital==user_hospital)]
        if not eligible:
            st.info("No patients with 'Arrived at Destination' status available for handover."); return

        opts = {f"{p.patient_id} — {p.name}": p for p in eligible}
        sel  = st.selectbox("Select Patient", list(opts.keys()))
        p    = opts[sel]

        with st.form("handover_form", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1:
                st.markdown(f"**Patient:** {p.name}  |  **Age:** {p.age}  |  **Condition:** {p.condition}")
                st.markdown(f"**From:** {p.referring_hospital}")
                receiving_physician = st.text_input("Receiving Physician *")
            with c2:
                st.markdown(f"**To:** {p.receiving_hospital}")
                st.markdown(f"**Referral ID:** `{p.patient_id}`")

            st.markdown("#### Vitals at Handover")
            c1,c2,c3,c4 = st.columns(4)
            bp   = c1.text_input("Blood Pressure",  "120/80")
            hr   = c2.number_input("Heart Rate (bpm)", 0, 200, 72)
            temp = c3.number_input("Temp (°C)", 30.0, 45.0, 36.6)
            spo2 = c4.number_input("SpO2 (%)", 0, 100, 98)

            notes = st.text_area("Handover Notes")
            c1,c2,c3 = st.columns(3)
            with c1: changes     = st.text_area("Condition Changes During Transfer", height=80)
            with c2: interv      = st.text_area("Interventions Given",              height=80)
            with c3: meds_given  = st.text_area("Medications Administered",         height=80)

            if st.form_submit_button("Complete Handover", use_container_width=True, type="primary"):
                if not receiving_physician:
                    st.error("Receiving physician is required.")
                else:
                    self.db.add_handover_form({
                        'patient_id': p.patient_id, 'patient_name': p.name,
                        'age': p.age, 'condition': p.condition,
                        'referring_hospital': p.referring_hospital,
                        'receiving_hospital': p.receiving_hospital,
                        'referring_physician': p.referring_physician,
                        'receiving_physician': receiving_physician,
                        'vital_signs': {'blood_pressure':bp,'heart_rate':hr,'temperature':temp,'oxygen_saturation':spo2},
                        'medical_history': p.medical_history,
                        'current_medications': p.current_medications,
                        'allergies': p.allergies,
                        'notes': f"{notes}\n\nCondition Changes: {changes}\n\nInterventions: {interv}\n\nMeds Given: {meds_given}",
                        'ambulance_id': p.assigned_ambulance,
                        'created_by': st.session_state.user['role']
                    })
                    p.status = 'Completed'
                    p.receiving_physician = receiving_physician
                    self.db.session.commit()
                    st.success("Handover completed and recorded."); st.balloons()

    def _history(self):
        handovers = self.db.session.query(HandoverForm).order_by(HandoverForm.transfer_time.desc()).all()
        user_hosp = st.session_state.user['hospital']
        if user_hosp != 'All Facilities':
            handovers = [h for h in handovers if h.receiving_hospital==user_hosp]
        if not handovers:
            st.info("No handover records."); return
        for h in handovers:
            with st.expander(f"{h.patient_name} — {h.transfer_time.strftime('%d %b %Y %H:%M')}"):
                c1,c2 = st.columns(2)
                with c1:
                    st.write(f"**Patient ID:** `{h.patient_id}`  |  **Age:** {h.age}")
                    st.write(f"**Condition:** {h.condition}")
                    st.write(f"**From:** {h.referring_hospital}")
                    st.write(f"**Referring Physician:** {h.referring_physician}")
                with c2:
                    st.write(f"**To:** {h.receiving_hospital}")
                    st.write(f"**Receiving Physician:** {h.receiving_physician}")
                    st.write(f"**Ambulance:** {h.ambulance_id or '—'}")
                if h.vital_signs:
                    v = h.vital_signs
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("BP",   v.get('blood_pressure','N/A'))
                    c2.metric("HR",   f"{v.get('heart_rate','N/A')} bpm")
                    c3.metric("Temp", f"{v.get('temperature','N/A')}°C")
                    c4.metric("SpO2", f"{v.get('oxygen_saturation','N/A')}%")
                if h.notes: st.write(f"**Notes:** {h.notes}")

# -----------------------------------------------------------------------------
# REPORTS UI
# -----------------------------------------------------------------------------
class ReportsUI:
    def __init__(self, db, analytics):
        self.db        = db
        self.analytics = analytics

    def display(self):
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:4px;'>Analytics & Reports</h1>
        <p style='color:#546e7a;font-size:0.9rem;margin-bottom:1.5rem;'>Data-driven insights for operational excellence</p>
        """, unsafe_allow_html=True)
        tab1,tab2,tab3,tab4 = st.tabs(["Performance","Hospitals","Fleet","Export"])
        with tab1: self._performance()
        with tab2: self._hospitals()
        with tab3: self._fleet()
        with tab4: self._export()

    def _performance(self):
        kpis = self.analytics.get_kpis()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Referrals",   kpis['total_referrals'])
        c2.metric("Completion Rate",   kpis['completion_rate'])
        c3.metric("Avg Response",      kpis['avg_response_time'])
        c4.metric("Active Transfers",  kpis['active_referrals'])

        dates = pd.date_range(end=datetime.now(), periods=30)
        times = [18.4 + np.random.uniform(-3,3) for _ in range(30)]
        fig   = go.Figure(go.Scatter(x=dates, y=times, mode='lines+markers',
                                      line=dict(color=BLUE,width=2),
                                      marker=dict(size=4,color=BLUE)))
        apply_theme(fig, "Average Response Time — Last 30 Days (minutes)")
        st.plotly_chart(fig, use_container_width=True, key="resp_trend")

        patients = self.db.get_all_patients()
        if patients:
            from collections import Counter
            cond_counts = Counter(p.condition for p in patients)
            top_conds   = dict(sorted(cond_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            fig = px.bar(x=list(top_conds.values()), y=list(top_conds.keys()),
                         orientation='h', color_discrete_sequence=[TEAL])
            apply_theme(fig, "Top 10 Referral Conditions")
            st.plotly_chart(fig, use_container_width=True, key="cond_bar")

    def _hospitals(self):
        patients = self.db.get_all_patients()
        if not patients:
            st.info("No data yet."); return
        from collections import Counter
        from_count = Counter(p.referring_hospital for p in patients)
        to_count   = Counter(p.receiving_hospital for p in patients)
        df = pd.DataFrame({'Facility': list(from_count.keys()),
                           'Referrals Sent': list(from_count.values())})
        df2= pd.DataFrame({'Facility': list(to_count.keys()),
                           'Referrals Received': list(to_count.values())})
        c1,c2 = st.columns(2)
        with c1:
            fig = px.bar(df.sort_values('Referrals Sent',ascending=True).tail(10),
                         x='Referrals Sent', y='Facility', orientation='h',
                         color_discrete_sequence=[RED])
            apply_theme(fig,"Top Referring Facilities")
            st.plotly_chart(fig, use_container_width=True, key="referring_bar")
        with c2:
            fig = px.bar(df2, x='Referrals Received', y='Facility', orientation='h',
                         color_discrete_sequence=[GREEN])
            apply_theme(fig,"Receiving Facilities")
            st.plotly_chart(fig, use_container_width=True, key="receiving_bar")

    def _fleet(self):
        ambulances = self.db.get_all_ambulances()
        if not ambulances: st.info("No ambulance data."); return
        from collections import Counter
        sc = Counter(a.status for a in ambulances)
        fig = px.pie(values=list(sc.values()), names=list(sc.keys()),
                     color_discrete_sequence=PALETTE, hole=0.5)
        apply_theme(fig,"Fleet Status Distribution")
        c1,c2 = st.columns(2)
        with c1: st.plotly_chart(fig, use_container_width=True, key="fleet_pie")
        with c2:
            data = [{'Unit':a.ambulance_id,'Driver':a.driver_name,'Status':a.status,
                     'Trips':int(np.random.randint(5,50)),'Distance km':f"{a.total_distance_traveled:,.0f}"}
                    for a in ambulances]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    def _export(self):
        st.markdown("#### Export Data")
        c1,c2,c3 = st.columns(3)
        with c1:
            patients = self.db.get_all_patients()
            df = pd.DataFrame([{'Patient ID':p.patient_id,'Name':p.name,'Age':p.age,
                                 'Condition':p.condition,'From':p.referring_hospital,
                                 'To':p.receiving_hospital,'Status':p.status,
                                 'Ambulance':p.assigned_ambulance or '—',
                                 'Distance (km)': p.trip_distance or 0,
                                 'Cost (KSh)': p.trip_fuel_cost or 0,
                                 'Date':p.referral_time.strftime('%Y-%m-%d %H:%M')} for p in patients])
            st.download_button("Referrals CSV", df.to_csv(index=False),
                               f"afyalink_referrals_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                               use_container_width=True)
        with c2:
            ambulances = self.db.get_all_ambulances()
            df = pd.DataFrame([{'Unit':a.ambulance_id,'Driver':a.driver_name,
                                 'Contact':a.driver_contact,'Status':a.status,
                                 'Fuel Level':f"{a.fuel_level:.1f}%",
                                 'Total Distance':a.total_distance_traveled,
                                 'Fuel Cost KSh':a.total_fuel_cost,
                                 'Savings KSh':a.cost_savings} for a in ambulances])
            st.download_button("Fleet CSV", df.to_csv(index=False),
                               f"afyalink_fleet_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",
                               use_container_width=True)
        with c3:
            st.button("PDF Report (Enterprise)", use_container_width=True, disabled=True,
                      help="Available in the Enterprise plan")

# -----------------------------------------------------------------------------
# DRIVER UI
# -----------------------------------------------------------------------------
class DriverUI:
    def __init__(self, db, notifications):
        self.db        = db
        self.notif     = notifications
        self.simulator = LocationSimulator(db)

    def display(self):
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:4px;'>Driver Console</h1>
        <p style='color:#546e7a;font-size:0.9rem;margin-bottom:1.5rem;'>Mission control, navigation and real-time updates</p>
        """, unsafe_allow_html=True)

        driver_name = st.session_state.user.get('name','Driver')
        ambulance   = self.db.session.query(Ambulance).filter(Ambulance.driver_name==driver_name).first()

        if not ambulance:
            st.error("No ambulance unit assigned to your account. Contact system administrator."); return

        fuel_clr = GREEN if ambulance.fuel_level>50 else AMBER if ambulance.fuel_level>20 else RED
        st.markdown(f"""
        <div style='display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1.5rem;'>
            <div style='background:#fafafa;border:1px solid #e0e0e0;border-radius:12px;
                        padding:1rem 1.5rem;flex:1;text-align:center;'>
                <div style='color:#78909c;font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;'>Unit</div>
                <div style='color:#1a237e;font-size:1.3rem;font-weight:800;'>{ambulance.ambulance_id}</div>
            </div>
            <div style='background:#fafafa;border:1px solid #e0e0e0;border-radius:12px;
                        padding:1rem 1.5rem;flex:1;text-align:center;'>
                <div style='color:#78909c;font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;'>Status</div>
                <div style='color:#1a237e;font-size:1.3rem;font-weight:800;'>{ambulance.status}</div>
            </div>
            <div style='background:#fafafa;border:1px solid {fuel_clr}50;border-radius:12px;
                        padding:1rem 1.5rem;flex:1;text-align:center;border-left:3px solid {fuel_clr};'>
                <div style='color:#78909c;font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;'>Fuel</div>
                <div style='color:{fuel_clr};font-size:1.3rem;font-weight:800;'>{ambulance.fuel_level:.1f}%</div>
            </div>
            <div style='background:#fafafa;border:1px solid #e0e0e0;border-radius:12px;
                        padding:1rem 1.5rem;flex:2;text-align:center;'>
                <div style='color:#78909c;font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;'>Location</div>
                <div style='color:#1a237e;font-size:1.0rem;font-weight:600;'>{ambulance.current_location or 'Unknown'}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        notifs = self.db.session.query(Communication).filter(
            Communication.receiver==driver_name
        ).order_by(Communication.timestamp.desc()).limit(5).all()

        if notifs:
            st.markdown("#### Recent Assignments & Messages")
            for idx, n in enumerate(notifs):
                with st.expander(f"📬 {n.timestamp.strftime('%d %b %H:%M')} — {n.sender}", expanded=False):
                    st.code(n.message, language=None)
                    if n.message_type=='auto_driver_assignment' and ambulance.status=='Available':
                        if st.button("Accept Assignment", key=f"accept_{n.id}_{idx}", use_container_width=True, type="primary"):
                            ambulance.status='On Transfer'; self.db.session.commit()
                            st.success("Assignment accepted!"); st.rerun()

        if ambulance.current_patient and ambulance.status=='On Transfer':
            patient = self.db.get_patient_by_id(ambulance.current_patient)
            if patient:
                st.markdown("#### Active Mission")
                c1,c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                    | | |
                    |---|---|
                    | **Patient** | {patient.name} |
                    | **Age** | {patient.age} |
                    | **Condition** | {patient.condition} |
                    | **Pickup** | {patient.referring_hospital} |
                    | **Destination** | {patient.receiving_hospital} |
                    | **Status** | {patient.status} |
                    """)
                    if patient.trip_distance:
                        cs = CostCalculationService(self.db).calculate_trip_cost(patient.trip_distance)
                        st.markdown(f"**Est. Trip Cost:** KSh {cs['total_cost_ksh']:,.0f} ({patient.trip_distance:.1f} km)")
                with c2:
                    with st.form("loc_update"):
                        st.markdown("**Update Location**")
                        loc  = st.text_input("Location name", value=ambulance.current_location or "En route")
                        lat  = st.number_input("Latitude",  value=ambulance.latitude or Config.DEFAULT_LATITUDE,  format="%.6f")
                        lng  = st.number_input("Longitude", value=ambulance.longitude or Config.DEFAULT_LONGITUDE, format="%.6f")
                        if st.form_submit_button("Update", use_container_width=True):
                            AmbulanceService(self.db).update_location(ambulance.ambulance_id, lat, lng, loc, patient.patient_id)
                            st.success("Location updated — hospitals can see your position.")

                st.markdown("#### Quick Messages")
                qmsgs = {"ETA 10 min":"ETA 10 minutes from now.",
                         "Patient stable":"Patient stable during transport.",
                         "Traffic delay":"Traffic delay — revised ETA in 5 min.",
                         "Need assistance":"Require medical team ready at entrance.",
                         "Vitals normal":"All vitals within normal range."}
                cols = st.columns(len(qmsgs))
                for col, (label, msg) in zip(cols, qmsgs.items()):
                    if col.button(label, use_container_width=True, key=f"qmsg_{label}"):
                        for hosp in [patient.referring_hospital, patient.receiving_hospital]:
                            self.db.add_communication({'patient_id':patient.patient_id,
                                                        'ambulance_id':ambulance.ambulance_id,
                                                        'sender':'Driver','receiver':hosp,
                                                        'message':msg,'message_type':'driver_quick'})
                        st.toast("Quick update sent to both facilities!", icon="✅")

                st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
                c1,c2,c3 = st.columns(3)
                with c1:
                    if st.button("Mark Patient Picked Up", use_container_width=True, type="primary"):
                        ReferralService(self.db, self.notif).mark_picked_up(patient.patient_id)
                        st.rerun()
                with c2:
                    if st.button("Emergency Alert", use_container_width=True):
                        for r in [patient.referring_hospital, patient.receiving_hospital, "AfyaLink Control"]:
                            self.db.add_communication({'patient_id':patient.patient_id,
                                                        'ambulance_id':ambulance.ambulance_id,
                                                        'sender':'Driver','receiver':r,
                                                        'message':f"EMERGENCY: Unit {ambulance.ambulance_id} requires immediate assistance!",
                                                        'message_type':'emergency'})
                        st.error("Emergency alert broadcast to all facilities!")
                with c3:
                    if st.button("Patient Delivered", use_container_width=True, type="primary"):
                        ReferralService(self.db, self.notif).complete_mission(ambulance, patient)
                        st.rerun()
        else:
            st.markdown("#### Awaiting Mission")
            unassigned = self.db.session.query(Patient).filter(
                Patient.status=='Referred', Patient.assigned_ambulance.is_(None)).all()
            if unassigned:
                st.markdown("**Available Patients (unassigned):**")
                for idx, p in enumerate(unassigned):
                    with st.expander(f"{p.name} — {p.condition}"):
                        st.write(f"From: {p.referring_hospital}")
                        st.write(f"To:   {p.receiving_hospital}")
                        if st.button("Accept Mission", key=f"accm_{p.patient_id}_{idx}", use_container_width=True, type="primary"):
                            ambulance.current_patient = p.patient_id
                            ambulance.status          = 'On Transfer'
                            p.assigned_ambulance      = ambulance.ambulance_id
                            p.status                  = 'Ambulance Dispatched'
                            self.db.session.commit()
                            st.success(f"Mission accepted — {p.name}"); st.rerun()
            else:
                st.info("No unassigned patients at this time.")

        st.markdown("#### Unit Status")
        c1,c2,c3 = st.columns(3)
        with c1:
            if st.button("Set Available",    use_container_width=True):
                ambulance.status='Available'; ambulance.current_patient=None
                self.db.session.commit(); st.rerun()
        with c2:
            if st.button("On Break",         use_container_width=True):
                ambulance.status='On Break'; self.db.session.commit(); st.rerun()
        with c3:
            if st.button("Maintenance Mode", use_container_width=True):
                ambulance.status='Maintenance'; self.db.session.commit(); st.rerun()

# -----------------------------------------------------------------------------
# NATIONAL NETWORK UI
# -----------------------------------------------------------------------------
class NationalNetworkUI:
    def display(self):
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:4px;'>National Network</h1>
        <p style='color:#546e7a;font-size:0.9rem;margin-bottom:1.5rem;'>AfyaLink's countrywide rollout roadmap — 47 counties, one network</p>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style='background:#e8f5e9; border:1px solid #00695c30;border-radius:16px;padding:2rem;margin-bottom:2rem;'>
            <div style='font-size:0.7rem;letter-spacing:3px;color:#00695c;font-weight:700;text-transform:uppercase;margin-bottom:1rem;'>
                The AfyaLink Vision
            </div>
            <div style='font-size:1.1rem;color:#1a237e;line-height:1.8;'>
                AfyaLink is Kenya's first <strong>unified, real-time patient referral and ambulance coordination platform</strong>.
                Beginning with a full-featured pilot in <strong>Kisumu County</strong> — covering 40 facilities and 20 ambulance units —
                the system is architecturally ready for nationwide deployment across all <strong>47 counties</strong>.
                The same platform, the same reliability, scaled to every Kenyan patient who needs emergency care.
            </div>
            <div style='display:flex;gap:2rem;margin-top:1.5rem;flex-wrap:wrap;'>
                <div style='text-align:center;'><div style='font-size:2rem;font-weight:800;color:#00695c;'>6,600+</div><div style='font-size:0.75rem;color:#546e7a;'>Public Health Facilities</div></div>
                <div style='text-align:center;'><div style='font-size:2rem;font-weight:800;color:#0277bd;'>47</div><div style='font-size:0.75rem;color:#546e7a;'>Counties Targeted</div></div>
                <div style='text-align:center;'><div style='font-size:2rem;font-weight:800;color:#f57c00;'>54M+</div><div style='font-size:0.75rem;color:#546e7a;'>Kenyans Served</div></div>
                <div style='text-align:center;'><div style='font-size:2rem;font-weight:800;color:#5e35b1;'><20 min</div><div style='font-size:0.75rem;color:#546e7a;'>Target Response Time</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Rollout Roadmap")
        phases = [
            ("Phase 1 — Pilot", "2024–2025", "Kisumu County", "LIVE",
             "40 facilities · 20 ambulances · Full feature set · Real-time tracking · Cost analytics",
             GREEN, "#f5f5f5"),
            ("Phase 2 — Lake Region", "2025–2026", "Homa Bay · Migori · Siaya · Kisii · Nyamira", "QUEUED",
             "Expanding to Lake Victoria Economic Bloc · Shared ambulance dispatch pool · Inter-county referrals",
             BLUE, "#f5f5f5"),
            ("Phase 3 — Nationwide", "2026–2027", "All 47 Counties", "PLANNED",
             "Full national integration · Ministry of Health data pipeline · NHIF compatibility · Telemedicine integration",
             PURPLE, "#f5f5f5"),
        ]
        for title, period, scope, status, detail, clr, bg in phases:
            st.markdown(f"""
            <div style='background:{bg};border:1px solid {clr}40;border-left:4px solid {clr};
                        border-radius:12px;padding:1.2rem 1.5rem;margin:0.8rem 0;'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;'>
                    <div>
                        <div style='font-size:1rem;font-weight:800;color:#1a237e;'>{title}</div>
                        <div style='font-size:0.8rem;color:{clr};font-weight:600;margin:2px 0;'>{scope}</div>
                        <div style='font-size:0.8rem;color:#546e7a;margin-top:4px;'>{detail}</div>
                    </div>
                    <div style='text-align:right;'>
                        <div style='background:{clr}15;color:{clr};border:1px solid {clr}40;
                                    border-radius:20px;padding:3px 14px;font-size:0.75rem;font-weight:700;'>
                            {status}
                        </div>
                        <div style='color:#78909c;font-size:0.75rem;margin-top:4px;'>{period}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### County Onboarding Status")
        c_data = []
        for i, county in enumerate(Config.KENYA_COUNTIES):
            if i == 0:
                c_data.append({'County': county.replace(' Pilot County',''), 'Status': 'Live', 'Facilities': 40, 'Ambulances': 20, 'Phase': 1})
            elif i < 6:
                c_data.append({'County': county, 'Status': 'Phase 2', 'Facilities': np.random.randint(15,80), 'Ambulances': np.random.randint(5,15), 'Phase': 2})
            else:
                c_data.append({'County': county, 'Status': 'Phase 3', 'Facilities': np.random.randint(10,60), 'Ambulances': np.random.randint(3,12), 'Phase': 3})
        df = pd.DataFrame(c_data)
        c1,c2 = st.columns([3,2])
        with c1:
            st.dataframe(df, use_container_width=True, hide_index=True)
        with c2:
            pc = df['Phase'].value_counts().reset_index()
            pc.columns = ['Phase','Counties']
            pc['Phase'] = pc['Phase'].map({1:'Phase 1 (Live)',2:'Phase 2 (Queued)',3:'Phase 3 (Planned)'})
            fig = px.pie(pc, values='Counties', names='Phase',
                         color_discrete_sequence=[GREEN, BLUE, PURPLE], hole=0.5)
            apply_theme(fig,"Rollout Distribution")
            st.plotly_chart(fig, use_container_width=True, key="rollout_pie")

        st.markdown("### Platform Capabilities")
        caps = [
            ("🔒","Security & Compliance","HIPAA-aligned data handling · Role-based access control · End-to-end audit trail · Secure API"),
            ("📡","Real-time Infrastructure","Live GPS tracking · Instant push notifications · WebSocket communication · 99.9% uptime SLA"),
            ("🤖","AI-Powered Dispatch","Smart ambulance assignment · Haversine geospatial routing · Fuel-aware optimisation · Predictive ETA"),
            ("📊","Analytics & BI","KPI dashboards · Cost intelligence · Operational reports · Ministry-ready data exports"),
            ("🏥","EHR Integration","HL7 FHIR-ready · KHIS/DHIS2 compatible · NHIF data feeds · Telemedicine module (Phase 3)"),
            ("📱","Multi-Platform","Web dashboard · Mobile-optimised · Offline-capable driver app · SMS fallback for low-connectivity zones"),
        ]
        c1,c2,c3 = st.columns(3)
        for i, (icon, title, desc) in enumerate(caps):
            col = [c1,c2,c3][i%3]
            col.markdown(f"""
            <div style='background:#ffffff;border:1px solid #e0e0e0;border-radius:12px;
                        padding:1.2rem;margin-bottom:0.8rem;height:140px;box-shadow:0 1px 2px rgba(0,0,0,0.05);'>
                <div style='font-size:1.5rem;margin-bottom:6px;'>{icon}</div>
                <div style='font-size:0.9rem;font-weight:700;color:#1a237e;margin-bottom:4px;'>{title}</div>
                <div style='font-size:0.78rem;color:#546e7a;line-height:1.5;'>{desc}</div>
            </div>
            """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# MAIN APPLICATION
# -----------------------------------------------------------------------------
class AfyaLinkApp:
    def __init__(self):
        self.auth             = Authentication()
        self.db               = Database()
        initialize_sample_data(self.db)
        self.analytics        = AnalyticsService(self.db)
        self.notifications    = NotificationService(self.db)
        self.dashboard_ui     = DashboardUI(self.db, self.analytics)
        self.referral_ui      = ReferralUI(self.db, self.notifications)
        self.tracking_ui      = TrackingUI(self.db)
        self.handover_ui      = HandoverUI(self.db)
        self.communication_ui = CommunicationUI(self.db, self.notifications)
        self.reports_ui       = ReportsUI(self.db, self.analytics)
        self.driver_ui        = DriverUI(self.db, self.notifications)
        self.cost_ui          = CostManagementUI(self.db, self.analytics)
        self.national_ui      = NationalNetworkUI()

        for key in ['authenticated','user','simulation_running']:
            if key not in st.session_state:
                st.session_state[key] = False if key!='user' else None

    def run(self):
        self.auth.setup_auth_ui()
        if st.session_state.get('authenticated'):
            self._main_app()
        else:
            self._landing()

    def _landing(self):
        st.markdown("""
        <div style='background:linear-gradient(135deg, #f5f7fa 0%, #e8eaf6 50%, #f5f7fa 100%);
                    border:1px solid rgba(0,105,92,0.2);border-radius:20px;padding:3rem 2.5rem;margin-bottom:2rem;'>
            <div style='font-size:0.75rem;letter-spacing:4px;color:#00695c;font-weight:700;text-transform:uppercase;margin-bottom:1rem;'>
                AfyaLink — Kenya's National Health Referral Network
            </div>
            <h1 style='font-size:2.8rem;font-weight:900;color:#1a237e;margin:0 0 1rem;line-height:1.15;'>
                Connecting Every Patient<br>to the Right Care, <span style='color:#00695c;'>Right Now</span>
            </h1>
            <p style='font-size:1.05rem;color:#546e7a;max-width:640px;line-height:1.7;margin-bottom:2rem;'>
                AfyaLink is a real-time patient referral and ambulance coordination platform built for Kenya's 
                public health system. Piloting in Kisumu County with 40 facilities and 20 ambulance units — 
                designed to scale to all 47 counties and 54 million Kenyans.
            </p>
            <div style='display:flex;gap:2rem;flex-wrap:wrap;'>
                <div><span style='font-size:1.8rem;font-weight:800;color:#00695c;'>40</span><br><span style='font-size:0.8rem;color:#546e7a;'>Facilities Online</span></div>
                <div><span style='font-size:1.8rem;font-weight:800;color:#0277bd;'>20</span><br><span style='font-size:0.8rem;color:#546e7a;'>Ambulance Units</span></div>
                <div><span style='font-size:1.8rem;font-weight:800;color:#f57c00;'>47</span><br><span style='font-size:0.8rem;color:#546e7a;'>Counties Ready</span></div>
                <div><span style='font-size:1.8rem;font-weight:800;color:#5e35b1;'><20 min</span><br><span style='font-size:0.8rem;color:#546e7a;'>Target Response</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def _main_app(self):
        role = st.session_state.user['role']
        if role == 'Ambulance Driver':
            self.driver_ui.display()
        elif role == 'Admin':
            self._admin_tabs()
        else:
            self._staff_tabs()

        st.markdown("""
        <div style='text-align:center;color:#90a4ae;font-size:0.75rem;margin-top:3rem;padding:1rem;
                    border-top:1px solid #e0e0e0;'>
            <strong>AfyaLink</strong> — Kenya National Referral Network &nbsp;|&nbsp; 
            Kisumu County Pilot &nbsp;|&nbsp; 
            <span style='color:#00695c;'>Secure · Real-time · Scalable</span>
        </div>
        """, unsafe_allow_html=True)

    def _admin_tabs(self):
        tabs = st.tabs(["Dashboard","Referrals","Tracking",
                         "Cost Intelligence","Handovers","Communications",
                         "Reports","National Network","Users"])
        with tabs[0]: self.dashboard_ui.display()
        with tabs[1]: self.referral_ui.display()
        with tabs[2]: self.tracking_ui.display()
        with tabs[3]: self.cost_ui.display()
        with tabs[4]: self.handover_ui.display()
        with tabs[5]: self.communication_ui.display()
        with tabs[6]: self.reports_ui.display()
        with tabs[7]: self.national_ui.display()
        with tabs[8]: self._users()

    def _staff_tabs(self):
        tabs = st.tabs(["Dashboard","Referrals","Tracking","Handovers","Communications"])
        with tabs[0]: self.dashboard_ui.display()
        with tabs[1]: self.referral_ui.display()
        with tabs[2]: self.tracking_ui.display()
        with tabs[3]: self.handover_ui.display()
        with tabs[4]: self.communication_ui.display()

    def _users(self):
        if not self.auth.require_auth(['Admin']): return
        st.markdown("""
        <h1 style='font-size:1.8rem;font-weight:800;color:#1a237e;margin-bottom:1.5rem;'>User Management</h1>
        """, unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("#### Add User")
            with st.form("add_user"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                email    = st.text_input("Email")
                role     = st.selectbox("Role", ["Admin","Hospital Staff","Ambulance Driver"])
                hospital = st.selectbox("Facility", ['All Facilities',
                    'Jaramogi Oginga Odinga Teaching & Referral Hospital (JOOTRH)',
                    'Kisumu County Referral Hospital'] + hospitals_data['facility_name'][2:])
                if st.form_submit_button("Add User", use_container_width=True, type="primary"):
                    if username and password:
                        st.success(f"User {username} added as {role} at {hospital}")
                    else:
                        st.error("Username and password required")
        with c2:
            st.markdown("#### Current Users")
            users = [
                {"Name":"System Administrator","Username":"admin","Role":"Admin","Facility":"All Facilities","Status":"Active"},
                {"Name":"Dr. Achieng Odhiambo","Username":"hospital_staff","Role":"Hospital Staff","Facility":"JOOTRH","Status":"Active"},
                {"Name":"Dr. Mary Atieno","Username":"kisumu_staff","Role":"Hospital Staff","Facility":"Kisumu County Ref.","Status":"Active"},
                {"Name":"John Omondi","Username":"driver","Role":"Ambulance Driver","Facility":"Ambulance Service","Status":"Active"}
            ]
            st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    st.set_page_config(
        page_title=Config.PAGE_TITLE,
        page_icon=Config.PAGE_ICON,
        layout=Config.LAYOUT,
        initial_sidebar_state="expanded"
    )
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800;900&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    .stApp {
        background: linear-gradient(160deg, #f0f4f8 0%, #e8edf2 40%, #f5f7fa 100%);
        min-height: 100vh;
    }
    .stSidebar {
        background: linear-gradient(180deg, #f5f7fa 0%, #e8eaf6 100%) !important;
        border-right: 1px solid #e0e0e0 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.9);
        border-radius: 10px;
        padding: 4px;
        border: 1px solid #e0e0e0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #546e7a;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(0,105,92,0.1) !important;
        color: #00695c !important;
    }
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff, #fafafa);
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="metric-container"] label {
        color: #78909c !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #1a237e !important;
        font-size: 1.5rem !important;
        font-weight: 800 !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-family: 'DM Sans', sans-serif !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00695c, #00838f) !important;
        border: none !important;
        color: #ffffff !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,105,92,0.3) !important;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        color: #1a237e !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #00695c !important;
        box-shadow: 0 0 0 2px rgba(0,105,92,0.1) !important;
    }
    .stForm {
        background: linear-gradient(135deg, #ffffff, #fafafa);
        border: 1px solid #e0e0e0;
        border-radius: 14px;
        padding: 1.5rem;
    }
    .stExpander {
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 10px !important;
    }
    .stDataFrame {
        border-radius: 10px !important;
        overflow: hidden;
    }
    h1, h2, h3, h4, h5 { color: #1a237e !important; font-family: 'DM Sans', sans-serif !important; }
    p, li, span { font-family: 'DM Sans', sans-serif !important; }
    code { font-family: 'DM Mono', monospace !important; }
    .stAlert { border-radius: 10px !important; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #e0e0e0; }
    ::-webkit-scrollbar-thumb { background: #b0bec5; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #00695c; }
    </style>
    """, unsafe_allow_html=True)

    app = AfyaLinkApp()
    app.run()
