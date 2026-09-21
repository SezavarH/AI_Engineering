# CI/CD and GitHub Actions

- CI/CD is a set of practices that automatically test and deliver your code every time you make a change, so bugs are caught early and new features reach users quickly and safely. - - - GitHub Actions is GitHub’s built-in tool that lets you define and run these automated workflows directly from your repository.

## Analogy

- Imagine a factory assembly line for software.

    - CI (Continuous Integration) is the quality-control station that automatically checks every new part (code change) the moment it arrives.
    - CD (Continuous Delivery/Deployment) is the rest of the line that packages the product and either gets it ready to ship or actually ships it to customers.
    - GitHub Actions is the programmable robot that runs the entire assembly line for you whenever someone pushes code.

## Sub-concepts

- Continuous Integration (CI)
    - Every time a developer pushes code or opens a pull request, an automated process builds the project and runs the tests. 
    - The goal is to detect integration problems as early as possible.

- Continuous Delivery vs Continuous Deployment
    - Continuous Delivery: the code is always in a deployable state; a human still decides when to release.
    - Continuous Deployment: every change that passes the tests is automatically released to production.
    - Most teams start with Continuous Delivery.

- Why CI/CD matters
    - Manual testing and deployment are slow and error-prone. 
    - Automation gives fast feedback, consistent environments, and the confidence to ship frequently.

- GitHub Actions core ideas
    - Workflow: a YAML file (usually in .github/workflows/) that describes what should happen.
    - Event / Trigger: what starts the workflow (push, pull request, schedule, etc.).
    - Job: a set of steps that run on the same runner (virtual machine).
    - Step: a single task (checkout code, install dependencies, run tests, build Docker image, deploy…).
    - Runner: the machine that executes the job (GitHub-hosted or self-hosted).
    - Actions: reusable pieces of code you can plug into steps (official or community-made).

## Code example

```YAML
# .github/workflows/ci.yml
name: CI                                                            # Just a title for this workflow

on:                                                                 # “Run this whenever someone pushes/pulls code”
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:                                                               # The list of work that needs to be done
  test:
    runs-on: ubuntu-latest                                          # GitHub-hosted runner

    steps:
      - name: Checkout code
        uses: actions/checkout@v4                                   # “First, download my code from GitHub”

      - name: Set up Python                                         # Just a human-readable label
        uses: actions/setup-python@v5                               # Use this ready-made tool that someone at GitHub already wrote.”
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest

      - name: Run tests
        run: pytest

  build:
    runs-on: ubuntu-latest
    needs: test                     # only run if tests passed

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t my-app:${{ github.sha }} .
```

**## Mini Project: Your First CI/CD with GitHub Actions**

Follow these steps exactly. This will give you a working CI pipeline (automatic testing) and a simple CD pipeline (automatic “deploy” simulation).

### Step-by-step

1. Go to your repository page on GitHub.

2. Click the **Actions** tab at the top.  
   This is where you will see the logs and status of every workflow run.

3. You can use GitHub’s ready-made templates, but in this exercise we will write our own from scratch (best for learning).

4. In your repository, create this folder and file:
   ```
   .github/workflows/test.yml
   ```

5. Paste this simple content into `test.yml` (this is your CI pipeline):

   ```yaml
   name: CI - Run Tests

   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   jobs:
     test:
       runs-on: ubuntu-latest

       steps:
         - name: Checkout code
           uses: actions/checkout@v4

         - name: Set up Python
           uses: actions/setup-python@v5
           with:
             python-version: "3.11"

         - name: Install dependencies
           run: |
             python -m pip install --upgrade pip
             pip install -r requirements.txt
             pip install pytest

         - name: Run tests
           run: pytest
   ```

6. Commit and push the file to the `main` branch.

7. GitHub Actions will automatically start running.  
   Go back to the **Actions** tab — you will see the workflow appear and turn green (success) or red (failure).  
   Click on it to see the detailed logs.

8. Now let’s add a simple CD pipeline.  
   Create a second file:
   ```
   .github/workflows/deploy.yml
   ```

   Paste this content (this is a safe “deploy” simulation):

   ```yaml
   name: CD - Deploy (Simulation)

   on:
     push:
       branches: [main]

   jobs:
     deploy:
       runs-on: ubuntu-latest
       needs: []               # in a real project you would put "test" here

       steps:
         - name: Checkout code
           uses: actions/checkout@v4

         - name: Simulate deployment
           run: |
             echo "Building Docker image..."
             echo "Pushing to registry..."
             echo "Deploying to production..."
             echo "Deployment successful!"
   ```

9. Commit and push `deploy.yml`.

10. Go to the **Actions** tab again.  
    You will now see two workflows:
    - **CI - Run Tests** (runs on every push and pull request)
    - **CD - Deploy (Simulation)** (runs only when you push to `main`)

---

### What you just achieved

- **CI**: Every time you push code or open a pull request, tests run automatically.
- **CD**: Every time you push to `main`, a deployment simulation runs.
- You can see all logs and results in the Actions tab.

---

### Next small improvements you can try later

- Make the CD job wait for the CI job to pass (`needs: test`).
- Replace the `echo` commands with real Docker build & push commands.
- Add a real deployment step (for example to Railway, Render, or a cloud provider).

You now have a complete, working mini CI/CD system.

## Resource

- https://youtu.be/YLtlz88zrLg?si=tdBz4ypSyB1aBN5N
- https://youtu.be/qoalS5ae7fk?si=npxj8CJyltjubLem