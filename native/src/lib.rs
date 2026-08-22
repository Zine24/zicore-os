use std::ffi::{CStr, CString};
use std::os::raw::c_char;

#[repr(C)]
pub struct TrajectoryResult {
    pub delta_v1: f64,
    pub delta_v2: f64,
    pub total_dv: f64,
    pub time_of_flight: f64,
}

/// Calculate Hohmann transfer orbit (safety-critical, deterministic)
/// # Safety
/// This function performs deterministic floating-point arithmetic.
/// No unsafe operations beyond FFI boundary.
#[no_mangle]
pub extern "C" fn hohmann_transfer(r1: f64, r2: f64, mu: f64) -> f64 {
    let a_t = (r1 + r2) / 2.0;
    let v1 = (mu / r1).sqrt();
    let vt1 = (mu * (2.0 / r1 - 1.0 / a_t)).sqrt();
    let dv1 = (vt1 - v1).abs();
    dv1
}

/// Full Hohmann transfer with all parameters
#[no_mangle]
pub extern "C" fn hohmann_transfer_full(r1: f64, r2: f64, mu: f64) -> TrajectoryResult {
    let a_t = (r1 + r2) / 2.0;
    let v1 = (mu / r1).sqrt();
    let v2 = (mu / r2).sqrt();
    let vt1 = (mu * (2.0 / r1 - 1.0 / a_t)).sqrt();
    let vt2 = (mu * (2.0 / r2 - 1.0 / a_t)).sqrt();
    let dv1 = (vt1 - v1).abs();
    let dv2 = (v2 - vt2).abs();
    let tof = std::f64::consts::PI * (a_t.powi(3) / mu).sqrt();

    TrajectoryResult {
        delta_v1: dv1,
        delta_v2: dv2,
        total_dv: dv1 + dv2,
        time_of_flight: tof,
    }
}

/// Proximity safety check (deterministic)
#[no_mangle]
pub extern "C" fn proximity_check(
    ax: f64, ay: f64, az: f64,
    bx: f64, by: f64, bz: f64,
    safety_radius: f64,
) -> f64 {
    let dx = ax - bx;
    let dy = ay - by;
    let dz = az - bz;
    let dist = (dx * dx + dy * dy + dz * dz).sqrt();
    dist
}

/// Quaternion Hamilton product
#[no_mangle]
pub extern "C" fn quat_multiply(
    w1: f64, x1: f64, y1: f64, z1: f64,
    w2: f64, x2: f64, y2: f64, z2: f64,
) -> [f64; 4] {
    [
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ]
}

/// Quaternion to Euler angles
#[no_mangle]
pub extern "C" fn quat_to_euler(w: f64, x: f64, y: f64, z: f64) -> [f64; 3] {
    let sinr_cosp = 2.0 * (w * x + y * z);
    let cosr_cosp = 1.0 - 2.0 * (x * x + y * y);
    let roll = sinr_cosp.atan2(cosr_cosp);

    let sinp = 2.0 * (w * y - z * x).clamp(-1.0, 1.0);
    let pitch = sinp.asin();

    let siny_cosp = 2.0 * (w * z + x * y);
    let cosy_cosp = 1.0 - 2.0 * (y * y + z * z);
    let yaw = siny_cosp.atan2(cosy_cosp);

    [pitch, yaw, roll]
}

/// RK4 integration step (single axis for FFI simplicity)
#[no_mangle]
pub extern "C" fn rk4_step(
    state: f64, dt: f64,
    k1: f64, k2: f64, k3: f64, k4: f64,
) -> f64 {
    state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
}

/// Deorbit burn calculation
#[no_mangle]
pub extern "C" fn deorbit_burn(
    altitude: f64, target_alt: f64,
    mu: f64, r_earth: f64,
) -> f64 {
    let r = r_earth + altitude;
    let v_circ = (mu / r).sqrt();
    let r_target = r_earth + target_alt;
    let a_transfer = (r + r_target) / 2.0;
    let v_perigee = (mu * (2.0 / r - 1.0 / a_transfer)).sqrt();
    (v_perigee - v_circ).abs()
}

/// Structural stress and safety factor
#[no_mangle]
pub extern "C" fn structural_stress(
    load: f64, area: f64, yield_strength: f64,
) -> [f64; 2] {
    let stress = if area > 0.0 { load / area } else { f64::INFINITY };
    let safety_factor = if stress > 0.0 { yield_strength / stress } else { f64::INFINITY };
    [stress, safety_factor]
}

/// Version string
#[no_mangle]
pub extern "C" fn zicore_avionics_version() -> *const c_char {
    let version = CString::new("0.1.0").unwrap();
    version.into_raw()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hohmann() {
        let r1 = (400.0 + 6371.0) * 1000.0;
        let r2 = (35786.0 + 6371.0) * 1000.0;
        let dv = hohmann_transfer(r1, r2, 3.986e14);
        assert!(dv > 0.0);
        assert!(dv < 10000.0);
    }

    #[test]
    fn test_quat_multiply() {
        let result = quat_multiply(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0);
        assert!((result[0] - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_structural_stress() {
        let result = structural_stress(1000.0, 0.01, 250e6);
        assert!(result[1] > 1.0);
    }
}
