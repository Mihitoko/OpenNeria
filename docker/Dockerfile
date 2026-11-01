FROM python:3.12

RUN useradd -m neria

COPY . /home/neria/app
RUN chown -R neria:neria /home/neria/app
USER neria

WORKDIR /home/neria/app
RUN pip install uv
RUN /home/neria/.local/bin/uv sync

CMD ["/home/neria/.local/bin/uv", "run", "python3", "runner.py"]