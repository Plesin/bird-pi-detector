#!/usr/bin/env python3
"""
EXIF data handling utilities for bird detection camera system
Embeds camera metadata directly into JPEG images
"""

import math
import os
try:
    import piexif
except ImportError:
    piexif = None


# Standard ISO values (1/3 stop increments)
_STANDARD_ISO = [
    100, 125, 160, 200, 250, 320, 400, 500, 640,
    800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 12800, 25600
]


def calculate_iso_from_gain(gain):
    """
    Calculate ISO from camera analog gain, rounded to nearest standard 1/3-stop value.
    Base ISO for Pi HQ camera is approximately 100.
    """
    if gain is None:
        return None
    raw_iso = 100 * float(gain)
    return min(_STANDARD_ISO, key=lambda s: abs(s - raw_iso))


def extract_exif_data(metadata):
    """Extract EXIF data from camera metadata"""
    if not metadata:
        return {}
    
    exif_data = {}
    
    # Exposure time in microseconds -> convert to shutter speed
    if metadata.get("ExposureTime"):
        exposure_us = metadata["ExposureTime"]
        # Convert microseconds to seconds, then to fractional format
        exposure_s = exposure_us / 1_000_000.0
        if exposure_s > 0:
            # Format as "1/xxx" for short exposures or decimal for long
            if exposure_s < 1:
                shutter_fraction = 1.0 / exposure_s
                exif_data["ShutterSpeed"] = f"1/{int(round(shutter_fraction))}"
            else:
                exif_data["ShutterSpeed"] = f"{exposure_s:.2f}s"
        exif_data["ExposureTime"] = exposure_us
    
    # ISO from analog gain
    if metadata.get("AnalogueGain"):
        iso = calculate_iso_from_gain(metadata["AnalogueGain"])
        exif_data["ISO"] = iso
    
    # Lens info (static values from LensConfig via camera metadata)
    for key in ("LensMake", "LensModel", "FocalLength", "FocalLengthIn35mm", "MaxAperture"):
        if metadata.get(key) is not None:
            exif_data[key] = metadata[key]

    # White balance
    if metadata.get("ColourTemperature"):
        exif_data["ColourTemperature"] = metadata["ColourTemperature"]
    if metadata.get("ColourGains"):
        exif_data["ColourGains"] = metadata["ColourGains"]  # (r_gain, b_gain)
    if metadata.get("AwbMode") is not None:
        exif_data["AwbMode"] = metadata["AwbMode"]  # camera preset setting

    # Scene brightness from Lux
    if metadata.get("Lux"):
        exif_data["Lux"] = float(metadata["Lux"])

    # Additional metadata for ImageDescription
    if metadata.get("AnalogueGain"):
        exif_data["AnalogueGain"] = float(metadata["AnalogueGain"])
    if metadata.get("DigitalGain"):
        exif_data["DigitalGain"] = float(metadata["DigitalGain"])
    if metadata.get("FocusDistance"):
        exif_data["FocusDistance"] = metadata["FocusDistance"]
    if metadata.get("SensorTemperature"):
        exif_data["SensorTemperature"] = float(metadata["SensorTemperature"])
    
    return exif_data


def embed_exif_in_image(filepath, exif_data):
    """Embed EXIF data directly into JPEG image"""
    if not piexif:
        print(f"  ⚠️  piexif not installed. Install with: pip install piexif")
        return False
    
    if not exif_data:
        return False
    
    try:
        # Create exif dict
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}}

        # DateTimeOriginal from filename (bird_YYYYMMDD_HHMMSS_N.jpg)
        try:
            parts = os.path.basename(filepath).split("_")
            if len(parts) >= 3 and len(parts[1]) == 8 and len(parts[2]) == 6:
                dt_str = f"{parts[1][:4]}:{parts[1][4:6]}:{parts[1][6:8]} {parts[2][:2]}:{parts[2][2:4]}:{parts[2][4:6]}"
                dt_bytes = dt_str.encode()
                exif_dict["0th"][piexif.ImageIFD.DateTime] = dt_bytes
                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt_bytes
                exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = dt_bytes
        except Exception:
            pass
        
        # Camera make/model
        exif_dict["0th"][piexif.ImageIFD.Make] = b"Raspberry Pi Foundation"
        exif_dict["0th"][piexif.ImageIFD.Model] = b"Raspberry Pi HQ Camera"

        # Focal length as rational (mm)
        if exif_data.get("FocalLength"):
            fl = int(exif_data["FocalLength"] * 10)
            exif_dict["Exif"][piexif.ExifIFD.FocalLength] = (fl, 10)

        # 35mm equivalent focal length (integer)
        if exif_data.get("FocalLengthIn35mm"):
            exif_dict["Exif"][piexif.ExifIFD.FocalLengthIn35mmFilm] = int(exif_data["FocalLengthIn35mm"])

        # Lens make/model
        if exif_data.get("LensModel"):
            exif_dict["Exif"][piexif.ExifIFD.LensModel] = exif_data["LensModel"].encode()
        if exif_data.get("LensMake"):
            exif_dict["Exif"][piexif.ExifIFD.LensMake] = exif_data["LensMake"].encode()

        # Max aperture is a fixed lens spec (widest the lens can open)
        # MaxApertureValue tag uses APEX units: Av = log2(FNumber²)
        if exif_data.get("MaxAperture"):
            apex_av = math.log2(exif_data["MaxAperture"] ** 2)
            exif_dict["Exif"][piexif.ExifIFD.MaxApertureValue] = (int(round(apex_av * 100)), 100)

        # Add ISO (tag 0x8827) - belongs in Exif IFD
        if "ISO" in exif_data:
            exif_dict["Exif"][piexif.ExifIFD.ISOSpeedRatings] = exif_data["ISO"]
        
        # Add exposure time (0x829A) as a rational (numerator, denominator)
        if "ExposureTime" in exif_data:
            exposure_us = exif_data["ExposureTime"]
            exposure_s = exposure_us / 1_000_000.0
            # Store as rational: 1/1000 or 1/250 etc
            if exposure_s < 1:
                numerator = 1
                denominator = int(round(1.0 / exposure_s))
            else:
                numerator = int(exposure_s)
                denominator = 1
            exif_dict["Exif"][piexif.ExifIFD.ExposureTime] = (numerator, denominator)
        
        # White balance: 0=auto, 1=manual (EXIF standard)
        # AwbMode OFF (0) means manual; everything else is auto
        awb_mode = exif_data.get("AwbMode")
        exif_dict["Exif"][piexif.ExifIFD.WhiteBalance] = 1 if awb_mode == 0 else 0

        # Colour space: 1 = sRGB
        exif_dict["Exif"][piexif.ExifIFD.ColorSpace] = 1

        # Light source — prefer the actual camera AWB preset, fall back to colour temp
        # Mapping from picamera2 AwbMode to EXIF LightSource tag values
        _AWB_TO_LIGHT_SOURCE = {
            1: 0,   # Auto -> Unknown
            2: 3,   # Incandescent -> Tungsten
            3: 3,   # Tungsten -> Tungsten
            5: 2,   # Indoor -> Fluorescent
            6: 1,   # Daylight -> Daylight
            7: 10,  # Cloudy -> Cloudy weather
        }
        if awb_mode is not None and awb_mode in _AWB_TO_LIGHT_SOURCE:
            exif_dict["Exif"][piexif.ExifIFD.LightSource] = _AWB_TO_LIGHT_SOURCE[awb_mode]
        elif exif_data.get("ColourTemperature"):
            # Fall back to guessing from measured colour temperature
            ct = exif_data["ColourTemperature"]
            if ct < 3300:
                light_source = 3   # Tungsten
            elif ct < 4000:
                light_source = 2   # Fluorescent
            elif ct < 5000:
                light_source = 17  # Warm daylight
            elif ct < 6000:
                light_source = 1   # Daylight
            elif ct < 7000:
                light_source = 10  # Cloudy
            else:
                light_source = 11  # Shade
            exif_dict["Exif"][piexif.ExifIFD.LightSource] = light_source

        # Brightness value (APEX) from Lux: BV = log2(Lux / 2.5)
        if exif_data.get("Lux") and exif_data["Lux"] > 0:
            bv = math.log2(exif_data["Lux"] / 2.5)
            # Store as signed rational (value * 100 / 100)
            bv_int = int(round(bv * 100))
            exif_dict["Exif"][piexif.ExifIFD.BrightnessValue] = (bv_int, 100)

        # Store extra data in ImageDescription
        comment_parts = []
        if exif_data.get("LensModel"):
            comment_parts.append(f"Lens={exif_data['LensModel']}")
        if exif_data.get("ColourTemperature"):
            comment_parts.append(f"CT={exif_data['ColourTemperature']}K")
        if exif_data.get("ColourGains"):
            r, b = exif_data["ColourGains"]
            comment_parts.append(f"WB={r:.2f}/{b:.2f}")
        if exif_data.get("Lux"):
            comment_parts.append(f"Lux={exif_data['Lux']:.1f}")
        if exif_data.get("AnalogueGain"):
            comment_parts.append(f"Gain={exif_data['AnalogueGain']:.2f}")
        if exif_data.get("DigitalGain"):
            comment_parts.append(f"DGain={exif_data['DigitalGain']:.2f}")
        if exif_data.get("SensorTemperature"):
            comment_parts.append(f"SensorTemp={exif_data['SensorTemperature']:.1f}C")
        if comment_parts:
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = " | ".join(comment_parts).encode()
        
        # Write EXIF data to image
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, filepath)
        return True
        
    except Exception as e:
        print(f"  ⚠️  Failed to embed EXIF data: {e}")
        return False


def load_exif_data(full_photo_path):
    """Read ISO and shutter speed EXIF from a JPEG file. Returns a dict with
    'ISO', 'ShutterSpeed', and optionally '_description'."""
    if not piexif:
        return {}

    if not os.path.isfile(full_photo_path):
        return {}

    try:
        exif_dict = piexif.load(full_photo_path)
        exif_data = {}

        if "Exif" in exif_dict:
            ifd_exif = exif_dict["Exif"]
            if piexif.ExifIFD.ISOSpeedRatings in ifd_exif:
                exif_data["ISO"] = ifd_exif[piexif.ExifIFD.ISOSpeedRatings]
            if piexif.ExifIFD.ExposureTime in ifd_exif:
                numerator, denominator = ifd_exif[piexif.ExifIFD.ExposureTime]
                if denominator > 0:
                    exposure_s = numerator / denominator
                    if exposure_s < 1:
                        exif_data["ShutterSpeed"] = f"1/{int(round(1.0 / exposure_s))}"
                    else:
                        exif_data["ShutterSpeed"] = f"{exposure_s:.2f}s"

        if "0th" in exif_dict and piexif.ImageIFD.ImageDescription in exif_dict["0th"]:
            try:
                desc = exif_dict["0th"][piexif.ImageIFD.ImageDescription]
                if isinstance(desc, bytes):
                    desc = desc.decode("utf-8", errors="ignore")
                exif_data["_description"] = desc
            except Exception:
                pass

        return exif_data

    except Exception:
        return {}
