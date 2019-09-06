FROM oraclelinux:7-slim
WORKDIR /function

RUN groupadd --gid 1000 fn && adduser --uid 1000 --gid fn fn

RUN  yum-config-manager --disable ol7_developer_EPEL && \
     yum-config-manager --enable ol7_optional_latest && \
     yum -y install python3 python3-devel gcc libaio oracle-release-el7 && \
     yum -y install oracle-instantclient19.3-basiclite && \
     rm -rf /var/cache/yum
ENV PATH=/usr/lib/oracle/19.3/client64/bin:$PATH
ENV ORACLE_HOME=/usr/lib/oracle/19.3/client64
ENV TNS_ADMIN=/tmp/dbwallet

RUN pip3 install fdk cx_oracle oci

COPY ./func.py /function/

ENTRYPOINT /usr/local/bin/fdk /function/func.py handler
