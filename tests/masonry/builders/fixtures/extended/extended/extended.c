#include <Python.h>


static PyObject *hello(PyObject *self) {
    return PyUnicode_FromString("Hello");
}


static PyMethodDef module_methods[] = {
    {
        "hello",
        (PyCFunction) hello,
        NULL,
        PyDoc_STR("Say hello.")
    },
    {NULL}
};


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


PyMODINIT_FUNC
PyInit_extended(void)
{
    PyObject *module;

    module = PyModule_Create(&moduledef);

    if (module == NULL)
        return NULL;

    return module;
}
