"""Streams the audio of an ESPHome microphone to the Sound Recognition service (protocol: service/soundrec/espstream.py).

The device waits on a TCP port; the service connects, proves it knows the password (the password itself is never sent)
and receives raw 16-bit, 16 kHz, mono audio. Needs the ESP-IDF framework (ESP32, ESP32-S3...).
"""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import microphone, text_sensor
from esphome.const import CONF_ID, CONF_MICROPHONE, CONF_PORT, CONF_PASSWORD, ENTITY_CATEGORY_DIAGNOSTIC

CODEOWNERS = ["@schawki"]
DEPENDENCIES = ["network", "microphone"]
AUTO_LOAD = ["text_sensor"]

CONF_GAIN = "gain"
CONF_INFO = "info"

ns = cg.esphome_ns.namespace("sound_recognition_stream")
SoundRecognitionStream = ns.class_("SoundRecognitionStream", cg.Component)


def _validate_password(value):
    value = cv.string_strict(value)
    if len(value) < 8:
        raise cv.Invalid("the password must have at least 8 characters (keep it in secrets.yaml)")
    return value


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(SoundRecognitionStream),
            cv.Required(CONF_MICROPHONE): cv.use_id(microphone.Microphone),
            cv.Required(CONF_PASSWORD): _validate_password,
            cv.Optional(CONF_PORT, default=6055): cv.port,
            # Multiplier applied to the samples (the INMP441 is quiet): 1.0 = unchanged, at most 32.
            cv.Optional(CONF_GAIN, default=1.0): cv.float_range(min=0.1, max=32.0),
            # Lets Home Assistant find this device (Sound Recognition panel > Sources). Keep it unless you add the source by hand.
            cv.Optional(CONF_INFO, default={"name": "Sound Recognition stream"}): text_sensor.text_sensor_schema(
                entity_category=ENTITY_CATEGORY_DIAGNOSTIC, icon="mdi:microphone-message"
            ),
        }
    ).extend(cv.COMPONENT_SCHEMA),
    cv.only_on_esp32,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    mic = await cg.get_variable(config[CONF_MICROPHONE])
    cg.add(var.set_microphone(mic))
    cg.add(var.set_password(config[CONF_PASSWORD]))
    cg.add(var.set_port(config[CONF_PORT]))
    cg.add(var.set_gain(config[CONF_GAIN]))
    info = await text_sensor.new_text_sensor(config[CONF_INFO])
    cg.add(var.set_info_sensor(info))
