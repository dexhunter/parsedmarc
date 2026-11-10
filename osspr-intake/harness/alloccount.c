/* Count PYMEM_DOMAIN_OBJ allocations. Python callbacks cannot wrap the
 * allocator (the callback would allocate and recurse), so the counter
 * lives here and the harness compiles it with the running interpreter.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>

static PyMemAllocatorEx orig;
static uint64_t n_malloc;
static uint64_t n_calloc;
static uint64_t n_realloc;
static int installed;

static void *hook_malloc(void *ctx, size_t size) {
    (void)ctx;
    n_malloc++;
    return orig.malloc(orig.ctx, size);
}

static void *hook_calloc(void *ctx, size_t nelem, size_t elsize) {
    (void)ctx;
    n_calloc++;
    return orig.calloc(orig.ctx, nelem, elsize);
}

static void *hook_realloc(void *ctx, void *ptr, size_t new_size) {
    (void)ctx;
    n_realloc++;
    return orig.realloc(orig.ctx, ptr, new_size);
}

static void hook_free(void *ctx, void *ptr) {
    (void)ctx;
    orig.free(orig.ctx, ptr);
}

static PyObject *start(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    if (!installed) {
        PyMem_GetAllocator(PYMEM_DOMAIN_OBJ, &orig);
        PyMemAllocatorEx hook = orig;
        hook.malloc = hook_malloc;
        hook.calloc = hook_calloc;
        hook.realloc = hook_realloc;
        hook.free = hook_free;
        PyMem_SetAllocator(PYMEM_DOMAIN_OBJ, &hook);
        installed = 1;
    }
    n_malloc = 0;
    n_calloc = 0;
    n_realloc = 0;
    Py_RETURN_NONE;
}

static PyObject *reset(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    n_malloc = 0;
    n_calloc = 0;
    n_realloc = 0;
    Py_RETURN_NONE;
}

static PyObject *count(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    /* Snapshot before creating the return value, which itself allocates. */
    uint64_t total = n_malloc + n_calloc + n_realloc;
    return PyLong_FromUnsignedLongLong(total);
}

static PyMethodDef methods[] = {
    {"start", start, METH_NOARGS, "Install the counter, if needed, and reset it."},
    {"reset", reset, METH_NOARGS, "Reset the counter to zero."},
    {"count", count, METH_NOARGS, "malloc + calloc + realloc since the last reset."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "alloccount", NULL, -1, methods,
};

PyMODINIT_FUNC PyInit_alloccount(void) { return PyModule_Create(&moduledef); }
