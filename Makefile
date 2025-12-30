deps:
	uv sync

lint: ruff ty

ruff:
	ruff check .
	ruff format .
	ruff check .

ty:
	ty .

generate-example-streamlit-app-manifest-yaml:
	python ./streamlit-operator/streamlit_app_spec_schema.py > example-streamlit-app.yaml

release: generate-example-streamlit-app-manifest-yaml
ifneq ($(shell git status --porcelain),)
	echo "Must commit changes before creating a release"
	exit 1
endif
	tag=$(shell python -c "from semver.version import Version; print(str(Version.parse('$(tag)')))")
ifndef tag
	echo "Got invalid tag"
	exit 1
endif
	git checkout -b release-$(tag)
	yq -i e '.version |= "$(tag)"' ./charts/streamlit-operator/Chart.yaml
	yq -i e '.appVersion |= "$(tag)"' ./charts/streamlit-operator/Chart.yaml

	git commit -a -m "Release prep for $(tag): bump chart version"
	$(eval commit=$(shell git rev-parse HEAD))
	echo "Created commit $(commit)"

	yq -i e '.gitRef |= "$(tag)"' ./charts/streamlit-operator/values.yaml
	git commit -a -m "Release prep for $(tag): bump ref in default values"

	git tag -a $(tag) -m "Release $(tag)"
	git push origin $(tag)

	# helm cm-push charts/streamlit-operator chartmuseum

	git checkout main
	git checkout release-$(tag) -- charts/streamlit-operator/Chart.yaml
	git commit -am "Release prep for $(tag): bump chart version"
