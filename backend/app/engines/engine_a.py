import time
import re
import math
from .base import BaseEngine, InferenceResult


class DeterministicEngine(BaseEngine):
    """Motor A: basado en reglas y solvers numericos para todos los modulos ZIO"""

    def __init__(self):
        self.modules = {
            "zihab": self._zihab,
            "zinav": self._zinav,
            "zisys": self._zisys,
            "zipower": self._zipower,
            "ziship": self._ziship,
            "zidrone": self._zidrone,
            "zirobot": self._zirobot,
            "zicomm": self._zicomm,
            "zieco": self._zieco,
            "zimed": self._zimed,
            "zicorex": self._zicorex,
            "zilink": self._zilink,
            "zivr": self._zivr,
            "zisec": self._zisec,
            "zicriogen": self._zicriogen,
            "zimaury": self._zimaury,
            "zty": self._zty,
        }

    async def infer(self, module: str, instruction: str, input_data: str) -> InferenceResult:
        t0 = time.time()
        handler = self.modules.get(module, self._default)
        output, confidence = handler(instruction, input_data)
        return InferenceResult(
            engine="engine_a",
            output=output,
            confidence=confidence,
            latency_ms=(time.time() - t0) * 1000,
            metadata={"type": "deterministic", "rules_fired": 1}
        )

    # ── ZIHab: Life support ──────────────────────────────────────────────
    def _zihab(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        o2 = float(vals.get("o2", 21.0))
        co2 = float(vals.get("co2", 0.04))
        temp = float(vals.get("temp", 22.0))
        pressure = float(vals.get("pressure", 101.3))

        alerts = []
        if o2 < 19.0:
            alerts.append(f"CRITICO: O2 peligroso ({o2}%). Evacuar inmediatamente.")
        elif o2 < 20.5:
            alerts.append(f"ALERTA: O2 bajo ({o2}%). Activar generador de oxigeno.")

        if co2 > 1.0:
            alerts.append(f"CRITICO: CO2 letal ({co2}%). Emergencia respiratoria.")
        elif co2 > 0.5:
            alerts.append(f"ALERTA: CO2 elevado ({co2}%). Aumentar scrubbing.")

        if temp > 40:
            alerts.append(f"CRITICO: Temperatura extrema ({temp}C). Tripulacion en riesgo.")
        elif temp > 30:
            alerts.append(f"ALERTA: Temperatura alta ({temp}C). Activar cooling.")
        elif temp < 15:
            alerts.append(f"ALERTA: Temperatura baja ({temp}C). Activar heating.")

        if pressure < 80:
            alerts.append(f"CRITICO: Presion baja ({pressure} kPa). Riesgo de descompresion.")
        elif pressure < 95:
            alerts.append(f"ALERTA: Presion reducida ({pressure} kPa). Verificar sellos.")

        if not alerts:
            return f"Habitat nominal. O2: {o2}%, CO2: {co2}%, Temp: {temp}C, Presion: {pressure} kPa", 0.95
        return "; ".join(alerts), 0.90

    # ── ZiNav: Navigation / orbital mechanics ────────────────────────────
    def _zinav(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        alt = float(vals.get("alt", 400))
        vel = float(vals.get("vel", 7.68))
        target_alt = float(vals.get("target_alt", 400))
        fuel = float(vals.get("fuel", 100))
        incl = float(vals.get("inclination", 51.6))

        inst_lower = instruction.lower()

        if "hohmann" in inst_lower or "transfer" in inst_lower:
            mu = 3.986e14
            r1 = (alt + 6371) * 1000
            r2 = (target_alt + 6371) * 1000
            a_t = (r1 + r2) / 2
            v1 = math.sqrt(mu / r1)
            v_t1 = math.sqrt(mu * (2 / r1 - 1 / a_t))
            dv1 = abs(v_t1 - v1)
            T = math.pi * math.sqrt(a_t ** 3 / mu)
            return f"Hohmann: dv1={dv1:.0f} m/s, Transfer time={T/3600:.1f}h", 0.93

        if "deorbit" in inst_lower:
            dv_deorbit = vel * 0.02 + alt * 0.0005
            return f"Deorbit burn: dv={dv_deorbit:.0f} m/s. Entry angle optimal.", 0.91

        if "inclination" in inst_lower:
            target_incl = float(vals.get("target_incl", 28.5))
            dv_incl = vel * abs(math.radians(target_incl - incl))
            return f"Inclination change: dv={dv_incl:.0f} m/s to {target_incl}deg", 0.89

        if fuel < 10:
            return f"CRITICO: Combustible critico ({fuel}%). Trayectoria de emergencia requerida.", 0.88
        elif fuel < 25:
            return f"ALERTA: Combustible bajo ({fuel}%). Optimizar trayectoria.", 0.90

        return f"Orbita nominal. Alt: {alt}km, Vel: {vel}km/s, Incl: {incl}deg, Fuel: {fuel}%", 0.94

    # ── ZiPWR: Power systems ─────────────────────────────────────────────
    def _zipower(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        solar = float(vals.get("solar", 0))
        battery = float(vals.get("battery", 100))
        load = float(vals.get("load", 0))
        bus_v = float(vals.get("grid_v", 28))

        alerts = []
        if battery < 15:
            alerts.append(f"CRITICO: Bateria critica ({battery}%). Corte de carga inminente.")
        elif battery < 30:
            alerts.append(f"ALERTA: Bateria baja ({battery}%). Reducir carga no esencial.")

        if load > solar * 1.2 and battery < 50:
            alerts.append(f"CRITICO: Sobrecarga ({load}W > {solar}W solar). Bateria se agota.")

        if bus_v < 24:
            alerts.append(f"CRITICO: Voltaje bajo ({bus_v}V). Posible fallo de bus electrico.")
        elif bus_v < 26:
            alerts.append(f"ALERTA: Voltaje reducido ({bus_v}V). Verificar reguladores.")

        if solar == 0 and battery < 80:
            alerts.append(f"ALERTA: Sin solar. Modo eclipse. Bateria: {battery}%")

        if not alerts:
            net = solar - load
            return f"Power nominal. Solar: {solar}W, Load: {load}W, Net: {'+'if net>=0 else ''}{net:.0f}W, Bat: {battery}%", 0.94
        return "; ".join(alerts), 0.89

    # ── ZiShip: Spacecraft status ────────────────────────────────────────
    def _ziship(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        hull = float(vals.get("hull", 100))
        thermal = float(vals.get("thermal", 0))
        radiation = float(vals.get("radiation", 100))
        propulsion = vals.get("propulsion", "nominal")

        alerts = []
        if hull < 50:
            alerts.append(f"CRITICO: Integridad del casco comprometida ({hull}%). Presurizar.")
        elif hull < 80:
            alerts.append(f"ALERTA: Danos en casco ({hull}%). Inspeccionar.")

        if thermal > 80:
            alerts.append(f"CRITICO: Carga termica critica ({thermal}kW). Activar ablacion.")
        elif thermal > 50:
            alerts.append(f"ALERTA: Carga termica elevada ({thermal}kW).")

        if radiation < 30:
            alerts.append(f"CRITICO: Escudo de radiacion comprometido ({radiation}%).")
        elif radiation < 60:
            alerts.append(f"ALERTA: Escudo de radiacion reducido ({radiation}%).")

        if propulsion != "nominal" and propulsion != "active":
            alerts.append(f"ALERTA: Propulsion en modo {propulsion}.")

        if not alerts:
            return f"Ship nominal. Hull: {hull}%, Thermal: {thermal}kW, Radiation: {radiation}%, Propulsion: {propulsion}", 0.93
        return "; ".join(alerts), 0.88

    # ── ZIDrone: Drone swarm ─────────────────────────────────────────────
    def _zidrone(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        deployed = float(vals.get("deployed", 0))
        total = float(vals.get("total", 12))
        battery = float(vals.get("battery", 100))
        signal = float(vals.get("signal", -50))
        range_km = float(vals.get("range", 10))

        alerts = []
        loss_pct = (1 - deployed / max(total, 1)) * 100

        if loss_pct > 50:
            alerts.append(f"CRITICO: Perdida masiva de drones ({loss_pct:.0f}% fuera de linea).")
        elif loss_pct > 20:
            alerts.append(f"ALERTA: Perdida de drones ({loss_pct:.0f}% fuera de linea).")

        if battery < 15:
            alerts.append(f"CRITICO: Bateria de enjambre critica ({battery}%). Retirar.")
        elif battery < 30:
            alerts.append(f"ALERTA: Bateria de enjambre baja ({battery}%).")

        if signal < -80:
            alerts.append(f"CRITICO: Senal critica ({signal}dBm). Perdida de control.")
        elif signal < -65:
            alerts.append(f"ALERTA: Senal debil ({signal}dBm).")

        if not alerts:
            return f"Enjambre operativo. {deployed}/{total} activos, Bat: {battery}%, Signal: {signal}dBm", 0.92
        return "; ".join(alerts), 0.87

    # ── ZIRobot: Robotic systems ─────────────────────────────────────────
    def _zirobot(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        active = float(vals.get("active", 3))
        total = float(vals.get("total", 5))
        joint_temp = float(vals.get("joint_temp", 40))
        load = float(vals.get("load", 0))
        max_load = float(vals.get("max_load", 10))

        alerts = []
        if active < total * 0.5:
            alerts.append(f"ALERTA: Solo {int(active)}/{int(total)} robots operativos.")

        if joint_temp > 80:
            alerts.append(f"CRITICO: Temperatura de articulaciones critica ({joint_temp}C). Parada.")
        elif joint_temp > 60:
            alerts.append(f"ALERTA: Temperatura de articulaciones alta ({joint_temp}C).")

        if load > max_load * 0.9:
            alerts.append(f"CRITICO: Carga cercana al maximo ({load}/{max_load}kg).")
        elif load > max_load * 0.7:
            alerts.append(f"ALERTA: Carga elevada ({load}/{max_load}kg).")

        if not alerts:
            return f"Robotica nominal. {int(active)}/{int(total)} activos, Joint: {joint_temp}C, Load: {load}kg", 0.93
        return "; ".join(alerts), 0.88

    # ── ZIComm: Communications ───────────────────────────────────────────
    def _zicomm(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        latency = float(vals.get("latency", 42))
        bandwidth = float(vals.get("bandwidth", 100))
        packet_loss = float(vals.get("packet_loss", 0))
        encryption = vals.get("encryption", "aes256")

        alerts = []
        if latency > 500:
            alerts.append(f"CRITICO: Latencia extrema ({latency}ms). Comunicacion comprometida.")
        elif latency > 200:
            alerts.append(f"ALERTA: Latencia elevada ({latency}ms). Posible ruido solar.")

        if packet_loss > 5:
            alerts.append(f"CRITICO: Perdida de paquetes critica ({packet_loss}%).")
        elif packet_loss > 1:
            alerts.append(f"ALERTA: Perdida de paquetes ({packet_loss}%). Verificar enlace.")

        if encryption != "aes256" and encryption != "quantum":
            alerts.append(f"ALERTA: Cifrado no estandar ({encryption}). Riesgo de seguridad.")

        if not alerts:
            return f"Comm nominal. Latency: {latency}ms, BW: {bandwidth}Mbps, Loss: {packet_loss}%, Enc: {encryption}", 0.94
        return "; ".join(alerts), 0.88

    # ── ZIEco: Ecology / ECLSS ───────────────────────────────────────────
    def _zieco(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        co2_scrub = float(vals.get("co2_scrub", 0))
        water_recovery = float(vals.get("water_recovery", 95))
        air_quality = float(vals.get("air_quality", 98))
        plant_health = float(vals.get("plant_health", 85))

        alerts = []
        if co2_scrub < 5:
            alerts.append(f"CRITICO: Scrubbing de CO2 fallido ({co2_scrub}g/h). Riesgo letal.")
        elif co2_scrub < 10:
            alerts.append(f"ALERTA: Scrubbing de CO2 reducido ({co2_scrub}g/h).")

        if water_recovery < 70:
            alerts.append(f"ALERTA: Recuperacion de agua baja ({water_recovery}%). Racionar.")
        elif water_recovery < 85:
            alerts.append(f"INFO: Recuperacion de agua reducida ({water_recovery}%).")

        if air_quality < 80:
            alerts.append(f"ALERTA: Calidad del aire degradada ({air_quality}).")

        if plant_health < 40:
            alerts.append(f"CRITICO: Plantas en peligro ({plant_health}%).")
        elif plant_health < 60:
            alerts.append(f"ALERTA: Plantas estresadas ({plant_health}%).")

        if not alerts:
            return f"Ecologia nominal. CO2 scrub: {co2_scrub}g/h, Water: {water_recovery}%, Air: {air_quality}, Plants: {plant_health}%", 0.93
        return "; ".join(alerts), 0.87

    # ── ZIMed: Medical ───────────────────────────────────────────────────
    def _zimed(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        health = float(vals.get("health", 94))
        hr = float(vals.get("hr", 72))
        bp_sys = float(vals.get("bp_sys", 120))
        bp_dia = float(vals.get("bp_dia", 80))
        radiation = float(vals.get("radiation", 0))

        alerts = []
        if health < 60:
            alerts.append(f"CRITICO: Estado de salud critico ({health}/100). Evacuar.")
        elif health < 80:
            alerts.append(f"ALERTA: Salud degradada ({health}/100).")

        if hr > 120 or hr < 45:
            alerts.append(f"CRITICO: Ritmo cardiaco anormal ({hr} bpm).")
        elif hr > 100:
            alerts.append(f"ALERTA: Taquicardia ({hr} bpm).")

        if bp_sys > 180 or bp_sys < 80:
            alerts.append(f"CRITICO: Presion arterial critica ({bp_sys}/{bp_dia}).")

        if radiation > 500:
            alerts.append(f"CRITICO: Exposicion a radiacion critica ({radiation}mSv).")
        elif radiation > 100:
            alerts.append(f"ALERTA: Radiacion elevada ({radiation}mSv). Monitorear.")

        if not alerts:
            return f"Tripulacion sana. Health: {health}/100, HR: {hr}bpm, BP: {bp_sys}/{bp_dia}, Rad: {radiation}mSv", 0.94
        return "; ".join(alerts), 0.89

    # ── ZICoreX: Computing ───────────────────────────────────────────────
    def _zicorex(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        load = float(vals.get("load", 60))
        mem_used = float(vals.get("mem_used", 8))
        mem_total = float(vals.get("mem_total", 16))
        queue = float(vals.get("queue", 0))
        nodes = float(vals.get("nodes", 4))

        alerts = []
        mem_pct = (mem_used / max(mem_total, 1)) * 100

        if load > 95:
            alerts.append(f"CRITICO: Sobrecarga de computo ({load}%). Cuello de botella.")
        elif load > 85:
            alerts.append(f"ALERTA: Carga de computo alta ({load}%).")

        if mem_pct > 90:
            alerts.append(f"CRITICO: Memoria agotada ({mem_pct:.0f}%). Riesgo de crash.")
        elif mem_pct > 75:
            alerts.append(f"ALERTA: Memoria elevada ({mem_pct:.0f}%).")

        if queue > 50:
            alerts.append(f"ALERTA: Cola de inferencia larga ({int(queue)} items).")

        if nodes < 2:
            alerts.append(f"ALERTA: Solo {int(nodes)} nodos activos. Redundancia comprometida.")

        if not alerts:
            return f"Computo nominal. Load: {load}%, Mem: {mem_pct:.0f}%, Queue: {int(queue)}, Nodes: {int(nodes)}", 0.93
        return "; ".join(alerts), 0.88

    # ── ZILink: Data link ────────────────────────────────────────────────
    def _zilink(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        rate = float(vals.get("rate", 10))
        margin = float(vals.get("margin", 10))
        optical = float(vals.get("optical", 4))
        rf = float(vals.get("rf", 2))

        alerts = []
        if margin < 3:
            alerts.append(f"CRITICO: Margen de enlace critico ({margin}dB). Perdida inminente.")
        elif margin < 6:
            alerts.append(f"ALERTA: Margen de enlace bajo ({margin}dB).")

        if rate < 1:
            alerts.append(f"CRITICO: Velocidad de datos muy baja ({rate}Gbps).")

        if optical + rf < 2:
            alerts.append(f"ALERTA: Pocos canales activos ({int(optical)}O / {int(rf)}RF).")

        if not alerts:
            return f"Data link nominal. Rate: {rate}Gbps, Margin: {margin}dB, Optical: {int(optical)}, RF: {int(rf)}", 0.93
        return "; ".join(alerts), 0.87

    # ── ZIVR: Virtual Reality ─────────────────────────────────────────────
    def _zivr(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        fps = float(vals.get("fps", 90))
        latency = float(vals.get("latency", 10))
        headsets = float(vals.get("headsets", 2))

        alerts = []
        if fps < 30:
            alerts.append(f"CRITICO: FPS criticos ({fps}). Nausea inminente.")
        elif fps < 60:
            alerts.append(f"ALERTA: FPS bajos ({fps}). Reducir calidad.")

        if latency > 50:
            alerts.append(f"CRITICO: Latencia VR critica ({latency}ms). Motion sickness.")
        elif latency > 20:
            alerts.append(f"ALERTA: Latencia VR elevada ({latency}ms).")

        if headsets < 1:
            alerts.append(f"ALERTA: Sin cascos VR conectados.")

        if not alerts:
            return f"VR nominal. FPS: {fps}, Latency: {latency}ms, Headsets: {int(headsets)}", 0.93
        return "; ".join(alerts), 0.88

    # ── ZISec: Security ──────────────────────────────────────────────────
    def _zisec(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        firewall = vals.get("firewall", "active")
        intrusions = float(vals.get("intrusions", 0))
        enc = vals.get("encryption", "aes256")
        auth = float(vals.get("auth_level", 5))

        alerts = []
        if firewall != "active":
            alerts.append("CRITICO: Firewall DESACTIVADO. Activar inmediatamente.")

        if intrusions > 10:
            alerts.append(f"CRITICO: {int(intrusions)} intrusiones en 24h. Ataque activo.")
        elif intrusions > 3:
            alerts.append(f"ALERTA: {int(intrusions)} intrusiones en 24h. Monitorear.")

        if enc == "none":
            alerts.append("CRITICO: Sin cifrado. Datos expuestos.")

        if auth < 3:
            alerts.append(f"ALERTA: Nivel de autorizacion bajo ({int(auth)}/5).")

        if not alerts:
            return f"Seguridad nominal. Firewall: {firewall}, Enc: {enc}, Intrusions: {int(intrusions)}, Auth: {int(auth)}/5", 0.94
        return "; ".join(alerts), 0.89

    # ── ZICriogen: Cryogenics ────────────────────────────────────────────
    def _zicriogen(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        temp = float(vals.get("temp", 20))
        pressure = float(vals.get("pressure", 100))
        fuel_level = float(vals.get("fuel_level", 90))
        boiloff = float(vals.get("boiloff", 0.1))

        alerts = []
        if temp > 120:
            alerts.append(f"CRITICO: Criogenico caliente ({temp}K). Propelente vaporizando.")
        elif temp > 80:
            alerts.append(f"ALERTA: Temperatura criogenica elevada ({temp}K).")

        if fuel_level < 20:
            alerts.append(f"ALERTA: Nivel de propelente criogenico bajo ({fuel_level}%).")

        if boiloff > 1:
            alerts.append(f"ALERTA: Boiloff excesivo ({boiloff}g/h). Verificar aislamiento.")

        if pressure > 300:
            alerts.append(f"CRITICO: Presion de tanque critica ({pressure}kPa).")
        elif pressure > 200:
            alerts.append(f"ALERTA: Presion de tanque alta ({pressure}kPa).")

        if not alerts:
            return f"Criogenia nominal. Temp: {temp}K, Pressure: {pressure}kPa, Fuel: {fuel_level}%, Boiloff: {boiloff}g/h", 0.93
        return "; ".join(alerts), 0.88

    # ── ZiMAUR: Defense / MAUR ───────────────────────────────────────────
    def _zimaury(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        personnel = float(vals.get("personnel", 4))
        readiness = float(vals.get("readiness", 4))
        drones = float(vals.get("drones", 6))
        shield = vals.get("shield", "active")
        mode = vals.get("mode", "patrol")

        alerts = []
        if personnel < 2:
            alerts.append(f"CRITICO: Solo {int(personnel)} personal disponible.")
        elif personnel < 4:
            alerts.append(f"ALERTA: Personal reducido ({int(personnel)}).")

        if readiness < 2:
            alerts.append(f"CRITICO: Nivel de preparacion critico ({int(readiness)}/5).")
        elif readiness < 3:
            alerts.append(f"ALERTA: Preparacion reducida ({int(readiness)}/5).")

        if shield != "active":
            alerts.append(f"CRITICO: Escudo {shield}. Vulnerables.")

        if mode == "combat":
            alerts.append(f"ALERTA: En modo combate. Todas las unidades en guardia.")

        if not alerts:
            return f"Defensa nominal. Personnel: {int(personnel)}, Readiness: {int(readiness)}/5, Shield: {shield}, Mode: {mode}", 0.93
        return "; ".join(alerts), 0.88

    # ── Z-TY: Aircraft factory ───────────────────────────────────────────
    def _zty(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        mass = float(vals.get("mass", 50000))
        dv = float(vals.get("dv", 9000))
        tw = float(vals.get("tw", 1.5))

        if tw < 1.0:
            return f"CRITICO: T/W < 1.0 ({tw:.2f}). Aeronave no despegara.", 0.85
        elif tw < 1.2:
            return f"ALERTA: T/W bajo ({tw:.2f}). Rendimiento marginal.", 0.88

        if dv < 3000:
            return f"ALERTA: Delta-v insuficiente ({dv:.0f}m/s). No alcanza orbita.", 0.86

        return f"Z-TY config validada. Mass: {mass:.0f}kg, dv: {dv:.0f}m/s, T/W: {tw:.2f}", 0.93

    # ── ZISys: General system status ─────────────────────────────────────
    def _zisys(self, instruction: str, data: str) -> tuple:
        vals = self._parse_kv(data)
        uptime = vals.get("uptime", "72h 14m")
        return f"Todos los sistemas nominales. Uptime: {uptime}", 0.96

    # ── Default: Unknown module ──────────────────────────────────────────
    def _default(self, instruction: str, data: str) -> tuple:
        return f"Comando recibido: {instruction[:50]}. Modulo no reconocido. Procesando...", 0.60

    # ── Key-value parser ─────────────────────────────────────────────────
    def _parse_kv(self, data: str) -> dict:
        result = {}
        try:
            import json
            d = json.loads(data)
            if isinstance(d, dict):
                for k, v in d.items():
                    result[str(k).lower()] = str(v)
                return result
        except (json.JSONDecodeError, TypeError):
            pass

        for match in re.finditer(r'(\w+)\s*[=:]\s*([\-]?\d+\.?\d*)', data):
            result[match.group(1).lower()] = match.group(2)
        for match in re.finditer(r'(\w+)\s*[=:]\s*([\w]+)', data):
            result[match.group(1).lower()] = match.group(2)
        return result
