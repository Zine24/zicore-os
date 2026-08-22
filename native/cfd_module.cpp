#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <cmath>
#include <vector>
#include <map>
#include <string>

namespace py = pybind11;

// ── Compressible Flow Relations ──────────────────────────────────

double speed_of_sound(double gamma, double R, double T) {
    return std::sqrt(gamma * R * T);
}

double mach_number(double velocity, double a) {
    return a > 0 ? velocity / a : 0.0;
}

double total_pressure_ratio(double mach, double gamma = 1.4) {
    double m2 = mach * mach;
    return std::pow(1.0 + 0.5 * (gamma - 1.0) * m2, gamma / (gamma - 1.0));
}

double total_temperature_ratio(double mach, double gamma = 1.4) {
    return 1.0 + 0.5 * (gamma - 1.0) * mach * mach;
}

// ── Boundary Layer ───────────────────────────────────────────────

struct BoundaryLayerResult {
    double thickness;
    double displacement_thickness;
    double momentum_thickness;
    double friction_coefficient;
    bool is_turbulent;
};

BoundaryLayerResult boundary_layer(double velocity, double x, double rho = 1.225, double mu = 1.81e-5) {
    double re_x = rho * velocity * x / mu;
    double transition_re = 5e5;
    BoundaryLayerResult result;

    if (re_x > transition_re) {
        // Turbulent (1/7th power law)
        result.thickness = 0.37 * x / std::pow(re_x, 0.2);
        result.displacement_thickness = result.thickness / 8.0;
        result.momentum_thickness = result.thickness * 7.0 / 72.0;
        result.friction_coefficient = 0.0592 / std::pow(re_x, 0.2);
        result.is_turbulent = true;
    } else {
        // Laminar Blasius
        result.thickness = 5.0 * x / std::sqrt(re_x);
        result.displacement_thickness = result.thickness / 3.0;
        result.momentum_thickness = result.thickness * 2.0 / 15.0;
        result.friction_coefficient = 0.664 / std::sqrt(re_x);
        result.is_turbulent = false;
    }

    return result;
}

// ── Shock Wave ───────────────────────────────────────────────────

struct ShockResult {
    double mach_downstream;
    double pressure_ratio;
    double wave_angle;
    bool is_shock;
};

ShockResult oblique_shock(double mach, double deflection_deg, double gamma = 1.4) {
    ShockResult result;
    if (mach <= 1.0 || deflection_deg <= 0) {
        result.mach_downstream = mach;
        result.pressure_ratio = 1.0;
        result.wave_angle = 0.0;
        result.is_shock = false;
        return result;
    }

    double deflection = deflection_deg * M_PI / 180.0;
    double beta = std::asin(1.0 / mach) + deflection * 0.5;
    if (beta > M_PI / 2.0 - 0.01) beta = M_PI / 2.0 - 0.01;

    double mn = mach * std::sin(beta);
    double mn2 = mn * mn;
    double p_ratio = 1.0 + 2.0 * gamma / (gamma + 1.0) * (mn2 - 1.0);
    double mn_down = std::sqrt((1.0 + 0.5 * (gamma - 1.0) * mn2) / (gamma * mn2 - 0.5 * (gamma - 1.0)));
    double mach_down = mn_down / std::sin(beta - deflection);

    result.mach_downstream = mach_down;
    result.pressure_ratio = p_ratio;
    result.wave_angle = beta * 180.0 / M_PI;
    result.is_shock = true;
    return result;
}

// ── Wave Drag ────────────────────────────────────────────────────

double wave_drag_coefficient(double mach, double thickness_ratio, double cl = 0.0) {
    if (mach <= 1.0) return 0.0;
    double m2 = mach * mach;
    double sqrt_term = std::sqrt(m2 - 1.0);
    double cd = 4.0 * thickness_ratio * thickness_ratio / sqrt_term;
    cd += 2.0 * cl * cl / sqrt_term;
    return cd;
}

// ── Induced Drag ─────────────────────────────────────────────────

double induced_drag_coefficient(double cl, double ar, double e = 0.85) {
    if (ar <= 0) return 0.0;
    return cl * cl / (M_PI * ar * e);
}

// ── Oswald Efficiency ────────────────────────────────────────────

double oswald_efficiency(double ar, double sweep_deg = 0.0) {
    double sweep = sweep_deg * M_PI / 180.0;
    double e = 1.78 * (1.0 - 0.045 * std::pow(ar, 0.68)) - 0.64;
    e *= std::pow(std::cos(sweep), 0.15);
    return std::max(0.5, std::min(0.95, e));
}

// ── Heat Flux ────────────────────────────────────────────────────

double stagnation_heat_flux(double rho, double velocity, double nose_radius) {
    if (velocity <= 0 || nose_radius <= 0) return 0.0;
    return 1.83e-4 * std::sqrt(rho / nose_radius) * std::pow(velocity, 3);
}

// ── Pressure Distribution ────────────────────────────────────────

std::vector<double> pressure_distribution(double mach, double cl, int n_points = 20) {
    std::vector<double> cp_list;
    double denom = 1.0 + 0.2 * mach * mach;
    for (int i = 0; i < n_points; ++i) {
        double x = static_cast<double>(i) / (n_points - 1);
        double cp;
        if (x <= 0.0) {
            cp = -cl * 2.0 / denom;
        } else if (x >= 1.0) {
            cp = 0.02;
        } else {
            cp = -cl * (1.0 - 2.0 * x) / denom + 0.01;
        }
        cp_list.push_back(cp);
    }
    return cp_list;
}

// ── Full Vehicle Analysis ────────────────────────────────────────

std::map<std::string, double> full_vehicle_analysis(
    double velocity, double altitude, double wing_area, double ar,
    double sweep_deg, double cl, double thickness_ratio)
{
    double rho = 1.225 * std::exp(-altitude / 8500.0);
    double mach = velocity / 343.0;
    double q = 0.5 * rho * velocity * velocity;

    double cd_wave = wave_drag_coefficient(mach, thickness_ratio, cl);
    double e = oswald_efficiency(ar, sweep_deg);
    double cd_induced = induced_drag_coefficient(cl, ar, e);
    double cd_friction = 0.003;
    double cd_total = cd_friction + cd_induced + cd_wave;
    double ld = cl / cd_total;
    double lift = cl * q * wing_area;
    double drag = cd_total * q * wing_area;

    auto bl = boundary_layer(velocity, 1.0, rho);

    return {
        {"mach", mach},
        {"dynamic_pressure", q},
        {"cl", cl},
        {"cd_total", cd_total},
        {"cd_friction", cd_friction},
        {"cd_induced", cd_induced},
        {"cd_wave", cd_wave},
        {"ld_ratio", ld},
        {"lift_force", lift},
        {"drag_force", drag},
        {"boundary_layer_mm", bl.thickness * 1000.0},
        {"friction_coefficient", bl.friction_coefficient},
        {"is_turbulent", bl.is_turbulent ? 1.0 : 0.0},
    };
}

// ── Python Bindings ──────────────────────────────────────────────

PYBIND11_MODULE(zicore_cfd, m) {
    m.doc() = "ZICORE C++ CFD Simulation Module";

    py::class_<BoundaryLayerResult>(m, "BoundaryLayerResult")
        .def_readonly("thickness", &BoundaryLayerResult::thickness)
        .def_readonly("displacement_thickness", &BoundaryLayerResult::displacement_thickness)
        .def_readonly("momentum_thickness", &BoundaryLayerResult::momentum_thickness)
        .def_readonly("friction_coefficient", &BoundaryLayerResult::friction_coefficient)
        .def_readonly("is_turbulent", &BoundaryLayerResult::is_turbulent);

    py::class_<ShockResult>(m, "ShockResult")
        .def_readonly("mach_downstream", &ShockResult::mach_downstream)
        .def_readonly("pressure_ratio", &ShockResult::pressure_ratio)
        .def_readonly("wave_angle", &ShockResult::wave_angle)
        .def_readonly("is_shock", &ShockResult::is_shock);

    m.def("speed_of_sound", &speed_of_sound, "Speed of sound",
          py::arg("gamma") = 1.4, py::arg("R") = 287.058, py::arg("T") = 288.15);
    m.def("mach_number", &mach_number, "Mach number");
    m.def("total_pressure_ratio", &total_pressure_ratio, "Total pressure ratio",
          py::arg("mach"), py::arg("gamma") = 1.4);
    m.def("total_temperature_ratio", &total_temperature_ratio, "Total temperature ratio",
          py::arg("mach"), py::arg("gamma") = 1.4);
    m.def("boundary_layer", &boundary_layer, "Boundary layer properties",
          py::arg("velocity"), py::arg("x"),
          py::arg("rho") = 1.225, py::arg("mu") = 1.81e-5);
    m.def("oblique_shock", &oblique_shock, "Oblique shock wave analysis",
          py::arg("mach"), py::arg("deflection_deg"), py::arg("gamma") = 1.4);
    m.def("wave_drag_coefficient", &wave_drag_coefficient, "Supersonic wave drag",
          py::arg("mach"), py::arg("thickness_ratio"), py::arg("cl") = 0.0);
    m.def("induced_drag_coefficient", &induced_drag_coefficient, "Induced drag",
          py::arg("cl"), py::arg("ar"), py::arg("e") = 0.85);
    m.def("oswald_efficiency", &oswald_efficiency, "Oswald efficiency factor",
          py::arg("ar"), py::arg("sweep_deg") = 0.0);
    m.def("stagnation_heat_flux", &stagnation_heat_flux, "Stagnation point heat flux");
    m.def("pressure_distribution", &pressure_distribution, "Pressure coefficient distribution",
          py::arg("mach"), py::arg("cl"), py::arg("n_points") = 20);
    m.def("full_vehicle_analysis", &full_vehicle_analysis, "Full aerodynamic vehicle analysis");

    m.attr("__version__") = "0.1.0";
}
