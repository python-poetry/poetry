#include <Python.h>


static PyObject *hello(PyObject *self) {
    return PyUnicode_FromString("Hello");
}


static PyMethodDef module_methods[] = {
    {
        "hello",
        (PyCFunction) hello,
        METH_NOARGS,
        PyDoc_STR("Say hello.")
    },
    {NULL}
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "extended",
    NULL,
    -1,
    module_methods,
    NULL,
    NULL,
    NULL,
    NULL,
};
#endif

PyMODINIT_FUNC
#if PY_MAJOR_VERSION >= 3
PyInit_extended(void)
#else
init_extended(void)
#endif
{
    PyObject *module;

#if PY_MAJOR_VERSION >= 3
    module = PyModule_Create(&moduledef);
#else
    module = Py_InitModule3("extended", module_methods, NULL);
#endif

    if (module == NULL)
#if PY_MAJOR_VERSION >= 3
        return NULL;
#else
        return;
#endif

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
