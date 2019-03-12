import sys
from pip._internal.req.req_file import preprocess, process_line


def main():
    filename = sys.argv[1]
    with open(filename, 'r') as f:
        content = f.read()

    reqs = []
    for n, line in preprocess(content, None):
        for req in process_line(line, filename, n):
            reqs.append(req)

    deps = reqs_to_poetry_deps(reqs)

    print('\n'.join(deps))


def reqs_to_poetry_deps(reqs):
    deps = []
    for req in reqs:
        r = req.req
        #print(dir(r.specifier._specs), dir(r.specifier))
        specs = r.specifier
        if len(specs._specs) > 0:
            spec = next(iter(specs._specs))
            #print(dir(spec))
            #print(spec.version, spec.operator)
            dep = '{} = "{}"'.format(r.name, spec)
        else:
            dep = ''
        deps.append(dep)
    return deps


if __name__ == '__main__':
    main()
