import os

# app.main and app.auth refuse to import without these secrets set (see the
# fail-fast checks added for the hardcoded-secret fix). Provide throwaway values
# for the test session before any app module is imported. pytest loads conftest
# before collecting test modules, so this runs first.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("SESSION_SECRET_KEY", "test-session-secret-not-for-production")
