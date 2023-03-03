FROM registry.suse.com/bci/bci-base:15.4.27.14.5

# Install needed RPMs 
RUN zypper --non-interactive in vim \
                                iputils \
																netcat-openbsd \
                                unzip \
                                tar \
																sudo \
                                gzip \
                                sysstat \
                                python3 \
                                python3-pip \
                                python3-cryptography \
                                python3-PyYAML



RUN pip install pymysql
RUN pip install inotify

# Install promtail
RUN curl -O -L https://github.com/grafana/loki/releases/download/v2.7.1/promtail-linux-amd64.zip
RUN unzip promtail-linux-amd64.zip
RUN cp promtail-linux-amd64 /usr/bin/
RUN mkdir /etc/promtail

# Install loki
RUN curl -O -L https://github.com/grafana/loki/releases/download/v2.7.1/loki-linux-amd64.zip
RUN unzip loki-linux-amd64.zip
RUN cp loki-linux-amd64 /usr/bin/
RUN mkdir /etc/loki/

# Install logcli
RUN curl -O -L https://github.com/grafana/loki/releases/download/v2.7.1/logcli-linux-amd64.zip
RUN unzip logcli-linux-amd64.zip
RUN cp logcli-linux-amd64 /usr/bin/

# Install node-exporter
RUN curl -O -L "https://github.com/prometheus/node_exporter/releases/download/v1.5.0/node_exporter-1.5.0.linux-amd64.tar.gz"
RUN tar xf node_exporter-1.5.0.linux-amd64.tar.gz
RUN cp node_exporter-1.5.0.linux-amd64/node_exporter /usr/bin/

RUN useradd -u 1000 -m tux
USER tux
 
 
