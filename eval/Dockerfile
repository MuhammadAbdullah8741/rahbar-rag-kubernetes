FROM rahbar-api:a3
WORKDIR /work
COPY --chown=10001:10001 api/app /work/api/app
COPY --chown=10001:10001 eval /work/eval
COPY --chown=10001:10001 config /work/config
ENV PYTHONPATH=/work/api
CMD ["python", "eval/suite.py"]
