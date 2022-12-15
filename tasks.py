from invoke import task


@task
def install(c):
    c.run('open *.indigoPlugin')
