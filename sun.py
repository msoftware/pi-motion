#!/usr/bin/python
# -*- coding: utf-8 -*-
# Dieses Programm berechnet näherungsweise den Zeitpunkt des Sonnenauf- und untergangs
# fuer einen bestimmten Tag und Ort. Die Sommerzeit wird beruecksichtigt.
# Geprueft wurde das Programm fuer die MEZ/MESZ.
# Quelle für die Berechnungen: https://lexikon.astronomie.info/zeitgleichung/index.html
# Jan Hartmann 2018 (mailto:jh1319@posteo.de)
# Das Programm darf ohne Einschränkungen verwendet, weitergegeben und modifiziert werden.

import math
import time
from datetime import date, datetime, timedelta

def days_between(date1, date2):
	ret = (date2-date1).days
	return ret

def getDiffToUTC(date):
	date2 = date + timedelta(days=1)
	t = time.mktime((date2).timetuple())
	offset = datetime.fromtimestamp(t) - datetime.utcfromtimestamp(t)
	diff = str(offset).split(':')[0]
	return int(diff)

def getSunsetSunrise(testdate, longitude, latitude):
	#Konvertiere date in datetime
	testdatetime=datetime.combine(testdate,datetime.min.time())
	#Bestimme die Nummer des Tages im Jahr
	T = days_between( date(testdate.year, 1, 1), testdate ) + 1
	B = math.pi * latitude / 180
	declination_sun = 0.4095 * math.sin( 0.016906 * ( T - 80.086 ))
	sunset_h = -0.0145
	#Zeitdifferenz
	time_diff = 12 * math.acos(( math.sin(sunset_h ) - math.sin( B ) * math.sin( declination_sun )) / ( math.cos( B ) * math.cos( declination_sun ))) / math.pi
	#Zeitgleichung
	time_equation = -0.171 * math.sin( 0.0337 * T + 0.465 ) - 0.1299 * math.sin( 0.01787 * T - 0.168 )

	#Sonnenauf- und untergang mittlere Ortszeit (MOZ)
	sunset_MOZ = 12 - time_diff - time_equation
	sunrise_MOZ = 12 + time_diff - time_equation
	#Differenz zwischen MOZ und MEZ/MESZ bestimmen
	MOZ_MEZ_diff = -longitude/15 + getDiffToUTC( testdate )
	#Uhrzeit MEZ/MESZ bestimmen
	sunset_MEZ_hours = sunset_MOZ + MOZ_MEZ_diff
	sunrise_MEZ_hours = sunrise_MOZ + MOZ_MEZ_diff
	#Stunden in Sekunden umrechnen
	sunset_MEZ_seconds = 3600 * sunset_MEZ_hours
	sunrise_MEZ_seconds = 3600 * sunrise_MEZ_hours
	#Uhrzeit von Sonnenauf- und untergang in das Tagesdatum integrieren
	sunset = testdatetime + timedelta( seconds = sunset_MEZ_seconds )
	sunrise = testdatetime + timedelta( seconds = sunrise_MEZ_seconds )

	return sunset, sunrise

