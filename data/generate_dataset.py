import json
import random
import math

random.seed(42)

MODULES = [
    "zinav", "ziaxis", "ziship", "zihab", "zieco", "zimed",
    "zipower", "zicriogen", "zidrone", "zirobot", "zicomm",
    "zilink", "zicorex", "zivr", "zisec", "zimaury", "zty",
]

TEMPLATES = {}

TEMPLATES["zinav"] = [
    ("calculate Hohmann transfer from {alt1}km to {alt2}km", "Burn 1: {dv1:.1f} m/s prograde at periapsis. Burn 2: {dv2:.1f} m/s circularize at apoapsis. Total delta-v: {total:.1f} m/s. Duration: {dur:.1f} min."),
    ("evaluate orbital insertion at {alt}km inclination {inc}deg", "Orbit: {alt}km x {alt}km, {inc}deg. Insertion burn: {dv:.1f} m/s. Stable. Next correction window: T+{t:.0f} min."),
    ("predict reentry corridor for {alt}km descent with {vel}km/s", "Corridor angle: {ang:.2f}deg. Peak heating: {heat:.0f} kW/m2. Landing dispersion: {disp:.1f} km. Guidance: nominal."),
    ("compute plane change maneuver from {inc1}deg to {inc2}deg at {alt}km", "Plane change delta-v: {dv:.1f} m/s. Optimal at equatorial crossing. Duration: {dur:.1f} min."),
    ("check collision risk with debris at {alt}km", "Objects tracked: {n}. Closest approach: {ca:.1f} km at T+{t:.1f}h. Risk: {risk}. {action}"),
    ("optimize transfer window to {target} departing {alt}km", "Window opens: {open}d. C3: {c3:.1f} km2/s2. Optimal delta-v: {dv:.1f} m/s. Launch window: {lw:.1f} min."),
    ("assess navigation accuracy at phase {phase}", "Position error: {pe:.1f} m. Velocity error: {ve:.2f} m/s. Clock bias: {cb:.1f} ns. Solution: {sol}."),
    ("plan station keeping for orbit {alt}km", "Drift rate: {dr:.2f} deg/day. Correction burn: {dv:.1f} m/s every {int:.0f} days. Fuel reserved: {fuel:.1f} kg."),
]

TEMPLATES["ziaxis"] = [
    ("compute gravitational gradient at {alt}km", "Gradient: {g:.2e} s-2. Tidal force on {len}m axis: {tf:.1f} N. Stability: {stab:.1f}%."),
    ("align gravitational axis to {angle}deg with mass distribution {dist}%", "Torque required: {tq:.1f} Nm. Alignment time: {t:.1f} min. Energy: {e:.1f} kJ. Status: {status}."),
    ("execute GPD descent from {alt}km with alignment {align}deg", "Descent path: {path} km. Peak deceleration: {dec:.1f} g. Targeting error: {err:.1f} m. GPD: {gpd}."),
    ("calculate tidal stress on vehicle length {len}m at {alt}km", "Axial stress: {stress:.1f} MPa. Shear: {shear:.1f} MPa. Safety margin: {sm:.1f}. {rec}"),
    ("evaluate gradient lock stability at {alt}km", "Lock stability: {ls:.1f}%. Restoring torque: {rt:.1f} Nm. Precession: {prec:.3f} deg/s. Status: {status}."),
    ("plan mass redistribution for GPD alignment target {angle}deg", "Mass to shift: {mass:.1f} kg. Pump power: {pow:.1f} W. Duration: {dur:.1f} min. Efficiency: {eff:.1f}%."),
]

TEMPLATES["ziship"] = [
    ("check hull integrity at thermal load {load}kW", "Integrity: {int:.1f}%. Stress hotspots: {n}. Max temp: {temp:.0f}C. {rec}"),
    ("manage propulsion transition to {mode} mode", "Transition: {dur:.1f}s. Thrust: {thrust:.1f} kN. Isp: {isp:.0f}s. Propellant: {prop:.1f} kg/s. {status}"),
    ("evaluate docking sequence with target at {range}m", "Approach velocity: {vel:.1f} m/s. Lateral error: {err:.1f} m. Docking port: {port}. {status}"),
    ("assess radiation shield effectiveness at {alt}km", "Shield: {shield:.0f}%. Dose rate: {dose:.2f} mSv/h. Remaining capacity: {cap:.1f}%."),
    ("monitor pressure hull integrity at {press}kPa", "Delta-p: {dp:.1f} kPa. Leak rate: {lr:.3f} g/s. Compressor: {comp} W. Status: {status}."),
    ("plan thermal management for {load}kW heat load", "Radiator area: {area:.1f} m2. Coolant flow: {flow:.1f} L/min. Pump power: {pow:.1f} W. Temp rise: {tr:.1f}C."),
]

TEMPLATES["zihab"] = [
    ("analyze life support with O2 {o2}% CO2 {co2}%", "O2 trend: {o2t}. CO2 trend: {co2t}. Scrubber: {scrub}%. Resupply in {res:.0f}h. {action}"),
    ("regulate temperature currently {temp}C target {target}C", "Heating: {heat:.0f}W. Cooling: {cool:.0f}W. Mixing: {mix:.1f}%. ETA: {eta:.1f} min."),
    ("check humidity at {hum}% and pressure {press}kPa", "Humidity trend: {humt}. Condensation risk: {cond}. Pressurization: {press:.1f} kPa. {action}"),
    ("assess air quality index {aqi}", "AQI: {aqi}. Particles: {part:.0f}/m3. VOCs: {voc:.1f} ppm. CO2: {co2:.1f} ppm. Filtration: {filt}%."),
    ("plan emergency O2 reserves for {crew} crew {days}d", "Required: {req:.0f} kg. Available: {avail:.0f} kg. Margin: {margin:.1f}d. {action}"),
    ("monitor water recycling efficiency at {rec}%", "Production: {prod:.1f} L/h. Quality: {qual} ppm TDS. Backup: {bup} L. Status: {status}."),
]

TEMPLATES["zieco"] = [
    ("evaluate CO2 scrubber efficiency at {rate}g/h", "Scrub rate: {rate:.1f} g/h. Media remaining: {media:.0f}%. Regeneration in {reg:.0f}h. Status: {status}."),
    ("check water recovery loop at {rec}% efficiency", "Recovery: {rec:.1f}%. Contaminants: {cont:.1f} ppm. UV treatment: {uv}%. Loop status: {status}."),
    ("assess plant health index {health}%", "Growth rate: {gr:.2f} mm/d. Light efficiency: {le:.1f}%. CO2 uptake: {cu:.1f} g/h. O2 production: {o2:.1f} g/h."),
    ("monitor waste recycling: {waste}kg processed", "Processing rate: {pr:.1f} kg/h. Output: {out} kg compost. Water recovered: {wr:.1f} L. Status: {status}."),
    ("analyze air quality index {aqi} and O2 generation {o2}g/h", "AQI: {aqi}. O2 gen: {o2:.1f} g/h. CO2 balance: {cb:.1f} g/h. Purity: {pur}%."),
    ("check atmospheric regeneration loop", "Loop flow: {flow:.1f} L/min. CO2 removal: {cr:.1f} g/h. O2 injection: {oi:.1f} g/h. Efficiency: {eff:.1f}%."),
]

TEMPLATES["zimed"] = [
    ("assess crew health index {index}/100 heart rate {hr}", "Index: {index}. HR: {hr}. BP: {bp}. Stress: {stress}. Fatigue: {fat}. {rec}"),
    ("monitor radiation exposure {dose}mSv cumulative", "Dose: {dose:.1f} mSv. Daily rate: {rate:.2f} mSv/d. Limit: {lim:.0f} mSv. Margin: {margin:.1f} mSv."),
    ("check medical supplies at {pct}% remaining", "Supplies: {pct:.0f}%. Critical items: {crit}. Resupply needed: {res}d. Expiry alerts: {exp}."),
    ("evaluate telemedicine link quality {qos}%", "QoS: {qos:.0f}%. Latency: {lat:.0f} ms. Bandwidth: {bw:.1f} Mbps. Diagnostic confidence: {conf:.0f}%."),
    ("plan exercise regimen for {crew} crew members", "Prescribed: {cardio} min cardio + {strength} min strength. Load: {load:.0f}%. Compliance: {comp:.0f}%."),
    ("monitor sleep patterns and cognitive performance", "Avg sleep: {sleep:.1f}h. Cognitive score: {cog:.0f}/100. Reaction time: {rt:.0f} ms. Alertness: {alert}."),
]

TEMPLATES["zipower"] = [
    ("balance solar input {solar}W with load {load}W", "Solar: {solar:.0f}W. Load: {load:.0f}W. Battery: {bat:.1f}%. Grid: {grid:.1f}V. {action}"),
    ("check battery state of charge {pct}%", "SoC: {pct:.0f}%. Voltage: {v:.1f}V. Temp: {temp:.1f}C. Cycle: {cyc}. Health: {health:.0f}%. {rec}"),
    ("assess power distribution across {n} buses", "Bus1: {b1:.0f}W. Bus2: {b2:.0f}W. Bus3: {b3:.0f}W. Redundancy: {red}. Load shed: {shed}."),
    ("evaluate solar panel efficiency at {angle}deg", "Efficiency: {eff:.1f}%. Degradation: {deg:.1f}%/yr. Output: {out:.0f}W. Tracking: {track}."),
    ("manage peak load of {load}W with {bat}% battery", "Peak: {load:.0f}W. Duration: {dur:.1f} min. Battery draw: {draw:.0f}W. Reserve: {res:.0f}%."),
    ("plan power-down sequence for maintenance", "Critical loads: {crit:.0f}W. Non-critical: {non:.0f}W. Backup duration: {backup:.1f}h. Sequence: {seq}."),
]

TEMPLATES["zicriogen"] = [
    ("monitor cryogenic propellant temp {temp}K pressure {press}kPa", "Temp: {temp:.1f}K. Press: {press:.1f}kPa. Boiloff: {boil:.2f} g/h. Insulation: {ins}. {rec}"),
    ("check fuel level {fuel}% oxidizer {ox}%", "Fuel: {fuel:.1f}%. Ox: {ox:.1f}%. Mix ratio: {mix:.3f}. Reserve: {res:.1f}%. Ullage: {ull:.1f}%."),
    ("assess boiloff rate {rate}g/h and insulation integrity", "Rate: {rate:.2f} g/h. Accumulated loss: {acc:.1f} kg. Insulation: {ins}. Temp gradient: {grad:.1f} K/m."),
    ("manage tank pressure at {press}kPa for engine feed", "Press: {press:.1f}kPa. Relief valve: {rv}. Auto-pressurization: {ap}%. Settling thrust: {st:.1f} N."),
    ("plan cryo transfer sequence for {fuel}kg fuel {ox}kg oxidizer", "Fuel transfer: {ft:.1f} kg/min. Ox transfer: {ot:.1f} kg/min. Duration: {dur:.1f} min. Chilldown: {cd:.1f} kg."),
    ("evaluate propellant stratification at {acc}g acceleration", "Temp stratification: {ts:.1f}K. Density gradient: {dg:.1f} kg/m3. Settling: {settle}. {rec}"),
]

TEMPLATES["zidrone"] = [
    ("deploy {n} drones for {mission} mission", "Deployed: {n}. Formation: {form}. Range: {rng:.1f} km. Battery: {bat:.1f}%. Link: {link}. {status}"),
    ("assess swarm status: {deployed}/{total} deployed", "Deployed: {deployed}. Standby: {total-deployed}. Avg battery: {bat:.1f}%. Lost link: {lost}. {action}"),
    ("evaluate survey coverage at {range}km range", "Area covered: {area:.1f} km2. Resolution: {res:.1f} m/px. Overlap: {ol:.1f}%. Data: {data:.1f} GB."),
    ("monitor drone battery levels avg {bat}%", "Min: {min:.1f}%. Max: {max:.1f}%. Returning: {ret}. Critical: {crit}. {action}"),
    ("plan search pattern for area {area}km2 with {n} drones", "Pattern: {pattern}. Spacing: {sp:.1f} m. Time: {time:.1f} min. Coverage: {cov:.1f}%. {rec}"),
    ("check communication relay signal {sig}dBm", "Signal: {sig:.1f} dBm. SNR: {snr:.1f} dB. Bitrate: {br:.1f} Mbps. Relays: {rel}. Status: {status}."),
]

TEMPLATES["zirobot"] = [
    ("check manipulator load {load}kg joint temp {temp}C", "Load: {load:.1f} kg. Joint temp: {temp:.1f}C. Torque: {tq:.1f} Nm. Vibration: {vib:.2f} mm. {rec}"),
    ("schedule {task} task with {n} robots", "Task: {task}. Robots: {n}. ETA: {eta:.1f} min. Tools: {tools}. Consumables: {con:.1f}%."),
    ("evaluate autonomy level {level} for precision operation", "Level: {level}. Positioning error: {pe:.1f} mm. Success rate: {sr:.1f}%. Intervention: {int}."),
    ("monitor robotic arm calibration offset {off}mm", "Offset: {off:.2f} mm. Encoder error: {ee:.2f} deg. Backlash: {bl:.2f} mm. {rec}"),
    ("assess collaborative robot safety zones", "Zones: {z}. Sensors: {sen}. Stop time: {st:.2f}s. Separation: {sep:.1f} m. Compliance: {comp}."),
    ("plan maintenance cycle for {n} robots, {task} pending", "Due: {due}. Overdue: {over}. Parts needed: {parts}. Labor: {lab:.1f}h. {action}"),
]

TEMPLATES["zicomm"] = [
    ("check link status {link} bandwidth {bw}Mbps latency {lat}ms", "Link: {link}. BW: {bw:.0f} Mbps. Lat: {lat:.0f} ms. Loss: {loss:.2f}%. SNR: {snr:.1f} dB."),
    ("assess network QoS metrics", "Throughput: {tp:.1f} Mbps. Jitter: {ji:.1f} ms. Packet loss: {pl:.2f}%. MOS: {mos:.1f}. {rec}"),
    ("evaluate encryption status {enc} on channel {ch}", "Encryption: {enc}. Key rotation: {kr:.0f}h. Auth: {auth}. Integrity: {integ}. Compliance: {comp}."),
    ("monitor antenna array tracking at {angle}deg elevation", "Array: {arr}. Gain: {gain:.1f} dBi. Pointing error: {pe:.2f} deg. Polarization: {pol}. {status}"),
    ("plan communications blackout procedure for {dur}min", "Duration: {dur:.0f} min. Store-and-forward: {sf:.1f} GB. Recovery: {rec}. Critical: {crit}."),
    ("check inter-satellite link budget margin {margin}dB", "Margin: {margin:.1f} dB. Modulation: {mod}. FEC: {fec}. Rain fade: {rf:.1f} dB. Status: {status}."),
]

TEMPLATES["zilink"] = [
    ("assess optical link quality on channel {ch}", "Optical link: {ch}. Bitrate: {br:.1f} Gbps. SNR: {snr:.1f} dB. Pointing: {pt:.2f} urad. {status}"),
    ("check RF link {n} at frequency {freq}GHz", "RF link: {n}. Freq: {freq:.2f} GHz. Power: {pow:.1f} dBm. Noise floor: {nf:.1f} dBm. {status}"),
    ("evaluate data rate {rate}Gbps on {n} channels", "Aggregate: {agg:.1f} Gbps. Channel utilization: {util:.1f}%. Errors: {err:.2e}. {rec}"),
    ("monitor link margin {margin}dB for atmospheric effects", "Margin: {margin:.1f} dB. Attenuation: {att:.1f} dB. Scintillation: {sci:.1f} dB. {status}"),
    ("plan handover between optical link {opt} and RF link {rf}", "Handover threshold: {thr:.1f} dB. Overlap: {ol:.1f}s. Switching time: {st:.1f}ms. {status}"),
    ("assess network topology with {n} active nodes", "Topology: {top}. Hops: {hops}. Diameter: {dia}. Redundancy: {red}. Latency: {lat:.1f} ms."),
]

TEMPLATES["zicorex"] = [
    ("check compute load {load}% memory {mem}GB/{total}GB", "Load: {load:.1f}%. Mem: {mem:.0f}/{total:.0f} GB. Swap: {swap:.1f} GB. Temp: {temp:.1f}C. {rec}"),
    ("evaluate inference queue depth {n}", "Queue: {n}. Avg latency: {lat:.1f}ms. Throughput: {tp:.1f} req/s. Backlog: {bl:.1f}s. {action}"),
    ("assess cluster health with {n} nodes", "Nodes: {n}. Active: {active}. Failed: {failed}. Load avg: {load:.2f}. Network: {net}."),
    ("monitor AI model {model} performance", "Model: {model}. Accuracy: {acc:.1f}%. Latency: {lat:.1f}ms. Memory: {mem:.1f} GB. {rec}"),
    ("plan distributed inference across {n} nodes", "Partition: {part}. Sync overhead: {sync:.1f}%. Speedup: {sp:.2f}x. Efficiency: {eff:.1f}%."),
    ("check storage system capacity {used}TB/{total}TB", "Used: {used:.1f}/{total:.1f} TB. IOPS: {iops:.0f}. Throughput: {tp:.1f} GB/s. Cache: {cache}%."),
]

TEMPLATES["zivr"] = [
    ("activate VR environment {env} for {n} headsets", "Environment: {env}. Headsets: {n}. FPS: {fps}. Latency: {lat:.0f} ms. Res: {res}. Haptics: {hap}."),
    ("check VR system performance at {fps}FPS", "FPS: {fps}. Frame time: {ft:.1f}ms. Reprojection: {rep:.1f}%. Motion-to-photon: {mtp:.0f}ms. {rec}"),
    ("evaluate simulation fidelity for {env} training", "Fidelity: {fid:.0f}%. Physics: {phys}. Visuals: {vis}. Audio: {aud}. Haptic: {hap}. {rec}"),
    ("monitor user presence and engagement metrics", "Users: {n}. Session: {dur:.1f}min. Heart rate: {hr:.0f}. Eye tracking: {eye}. Comfort: {comf}."),
    ("plan VR teleoperation session for {task}", "Task: {task}. Robot: {robot}. Video latency: {lat:.0f}ms. Control rate: {cr:.0f} Hz. {status}"),
    ("assess augmented reality overlay accuracy", "Overlay error: {err:.1f} mm. Registration: {reg}. Field of view: {fov:.0f}deg. Brightness: {bri}."),
]

TEMPLATES["zisec"] = [
    ("check firewall status {fw} and intrusion attempts {n}", "Firewall: {fw}. Blocks: {blk}. Rules: {rules}. Intrusions: {n}. Last event: {last}. {action}"),
    ("assess encryption posture for {n} channels", "Channels: {n}. Algorithm: {alg}. Key strength: {ks} bit. Rotation: {rot:.0f}h. Compliance: {comp}."),
    ("evaluate auth level {level}/5 for access control", "Level: {level}. Biometric: {bio}. MFA: {mfa}. Tokens: {tok}. Audit: {aud}. {rec}"),
    ("monitor network traffic anomalies", "Baseline: {base:.1f} Mbps. Current: {cur:.1f} Mbps. Anomalies: {anom}. Threats: {threat}. {action}"),
    ("plan security incident response for {type} threat", "Threat: {type}. Severity: {sev}. Containment: {con:.0f}s. Eradication: {era:.0f}s. Recovery: {rec:.0f}s."),
    ("check vulnerability scan results: {n} findings", "Critical: {crit}. High: {high}. Medium: {med}. Low: {low}. Patches: {patch}. {action}"),
]

TEMPLATES["zimaury"] = [
    ("assess tactical readiness level {level}/5", "Readiness: {level}/5. Personnel: {pers}. Equipment: {equip}%. Training: {train}%. {rec}"),
    ("check shield status: {shield} and weapon safety: {safe}", "Shield: {shield}. Power: {pow:.1f} kW. Capacity: {cap:.1f}%. Safety: {safe}. Interlock: {inter}."),
    ("deploy {n} armed drones for {mode} operation", "Drones: {n}. Mode: {mode}. Range: {rng:.1f} km. Loiter: {loit:.1f} min. Rules: {rules}."),
    ("evaluate perimeter defense coverage {cov}%", "Coverage: {cov:.1f}%. Gaps: {gaps}. Sensors: {sen}. Response: {resp:.1f}s. {rec}"),
    ("plan intercept course for unknown track at {range}km", "Track: {track}. Range: {rng:.1f} km. Speed: {spd:.1f} km/s. Intercept: {int:.1f} min. {action}"),
    ("monitor personnel readiness and alert status", "Personnel: {pers}. Alert: {alert}. Rest: {rest:.1f}h. Rotation: {rot:.0f}h. {rec}"),
]

TEMPLATES["zty"] = [
    ("analyze aircraft template {name}", "Template: {name}. Mass: {mass:.0f} kg. dV: {dv:.0f} m/s. T/W: {tw:.2f}. Payload: {pay:.0f} kg. {rec}"),
    ("compare {a} vs {b} for {mission} mission", "Winner: {win}. dV margin: {margin:.0f} m/s. Mass margin: {mm:.0f} kg. Cost: {cost}. {rec}"),
    ("design custom vehicle for payload {pay}kg target dV {dv}m/s", "Stages: {st}. Propellant: {prop:.0f} kg. Dry mass: {dry:.0f} kg. T/W: {tw:.2f}. Margin: {marg:.1f}%."),
    ("evaluate material {mat} for primary structure", "Material: {mat}. Density: {dens:.0f} kg/m3. Yield: {yield:.0f} MPa. Cost: {cost}. Suitability: {suit}."),
    ("optimize stage separation for {n}-stage vehicle", "Separation altitudes: {alt} km. Staging dV: {dv} m/s. Mass ratio: {mr:.3f}. Efficiency: {eff:.1f}%."),
]

def generate_value(v):
    if isinstance(v, str):
        try:
            parts = v.split(":")
            name = parts[0]
            mn, mx = float(parts[1]), float(parts[2])
            v = round(random.uniform(mn, mx), int(parts[3]) if len(parts) > 3 else 1)
            return v
        except:
            return v
    return v

def fill_template(template, ctx):
    try:
        result = template.format(**ctx)
        return result
    except KeyError:
        return template

def generate_dataset(samples_per_module=70):
    dataset = []
    ctx_defaults = {
        "alt": lambda: random.uniform(200, 42000),
        "alt1": lambda: random.uniform(200, 500),
        "alt2": lambda: random.uniform(500, 42000),
        "vel": lambda: random.uniform(1, 11),
        "inc": lambda: random.uniform(0, 98),
        "inc1": lambda: random.uniform(0, 51),
        "inc2": lambda: random.uniform(51, 98),
        "angle": lambda: random.uniform(-30, 30),
        "align": lambda: random.uniform(-15, 15),
        "dist": lambda: random.uniform(30, 70),
        "len": lambda: random.uniform(20, 150),
        "load": lambda: random.uniform(100, 2000),
        "temp": lambda: random.uniform(-50, 50),
        "press": lambda: random.uniform(50, 200),
        "o2": lambda: random.uniform(18, 22),
        "co2": lambda: random.uniform(0.01, 0.5),
        "target": ["Mars", "Luna", "Venus", "Ceres", "Europa"][:1],
        "phase": ["ascent", "transition", "orbital", "descent", "interplanetary"],
        "mode": ["ion", "chemical", "nuclear", "plasma"],
        "range": lambda: random.uniform(0.5, 100),
        "n": lambda: random.randint(1, 20),
        "pct": lambda: random.uniform(10, 100),
        "dose": lambda: random.uniform(0, 50),
        "solar": lambda: random.uniform(500, 3000),
        "bat": lambda: random.uniform(20, 100),
        "grid": lambda: random.uniform(24, 32),
        "fuel": lambda: random.uniform(30, 100),
        "ox": lambda: random.uniform(30, 100),
        "signal": lambda: random.uniform(-90, -30),
        "rate": lambda: random.uniform(0.1, 10),
        "fps": lambda: random.randint(30, 120),
        "lat": lambda: random.uniform(5, 200),
        "bw": lambda: random.uniform(10, 1000),
        "mem": lambda: random.uniform(16, 512),
        "total": lambda: random.uniform(256, 2048),
        "aqi": lambda: random.randint(0, 100),
        "crew": lambda: random.randint(2, 12),
        "index": lambda: random.randint(70, 100),
        "hr": lambda: random.randint(55, 100),
        "rec": lambda: random.uniform(70, 100),
        "deployed": lambda: random.randint(1, 20),
        "level": lambda: random.randint(1, 5),
        "shield": lambda: ["active", "charging", "standby", "damaged"],
    }

    def val(key, ctx_overrides):
        if key in ctx_overrides:
            v = ctx_overrides[key]
            if callable(v):
                return v()
            return v
        if key in ctx_defaults:
            v = ctx_defaults[key]
            if callable(v):
                return v()
            return v
        return 0

    def fill(text, overrides):
        import re
        def repl(m):
            key = m.group(1)
            fmt = m.group(2) or ""
            v = val(key, overrides)
            try:
                return format(v, fmt)
            except:
                return str(v)
        return re.sub(r'\{(\w+)(:.*?)?\}', repl, text)

    for module, templates in TEMPLATES.items():
        for i in range(samples_per_module):
            idx = i % len(templates)
            prompt_t, response_t = templates[idx]
            ctx = {}
            import re
            keys = set(re.findall(r'\{(\w+)\}', prompt_t + response_t))
            for k in keys:
                ctx[k] = val(k, ctx)
            prompt = fill(prompt_t, ctx)
            response = fill(response_t, ctx)
            dataset.append({
                "instruction": prompt,
                "output": response,
                "module": module,
            })
    return dataset

if __name__ == "__main__":
    ds = generate_dataset(70)
    print(f"Generated {len(ds)} examples")
    with open("zicore_training.jsonl", "w") as f:
        for item in ds:
            f.write(json.dumps(item) + "\n")
    print("Saved to zicore_training.jsonl")
    by_module = {}
    for item in ds:
        m = item["module"]
        by_module[m] = by_module.get(m, 0) + 1
    for m, c in sorted(by_module.items()):
        print(f"  {m}: {c}")
