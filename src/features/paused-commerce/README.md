# Paused commerce

This feature contains the legacy service catalog, direct booking, and course pages. Launch routing keeps these pages disabled and loads them only if their feature flags are enabled.

Keep new phase-one work in the active domain modules. Before restoring these pages, review their API contracts and align the user flow with the current service-request workflow. Booking and course API functions remain in their domain modules because the admin console still reads legacy records for compatibility.
