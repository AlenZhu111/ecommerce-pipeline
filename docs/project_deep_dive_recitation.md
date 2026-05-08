# E-Commerce Data Pipeline Deep-Dive Script

## 1. Project Pitch

I built an e-commerce event data pipeline using PySpark, Airflow, EC2, and S3.

The pipeline starts with Kaggle e-commerce behavior data. I sample the data for development, store the original input in a raw layer, inject controlled bad records into a corrupted layer, then run Spark jobs to perform data quality checks, clean invalid records, and produce analytics tables.

The final outputs are stored in S3 as curated Parquet and analytics Parquet. Airflow orchestrates the workflow so each step runs in the correct order and failures are visible.

The most valuable part was moving from local validation to AWS. I had to handle realistic issues like EC2 memory limits, Spark S3 path differences, PySpark environment configuration, and Kaggle file size constraints.

## 2. Architecture Walkthrough

The architecture has four main parts.

First, the data source is Kaggle e-commerce event data.

Second, S3 acts as the data lake. I use separate prefixes for raw, corrupted, curated, analytics, and reports.

Third, PySpark handles processing. It reads the corrupted input, runs quality checks, cleans invalid records, and creates aggregate tables.

Fourth, Airflow handles orchestration. It manages task order, checks that input exists, runs Spark jobs, and exposes logs.

The S3 layout is:

```text
raw/        original sampled input
corrupted/  input with injected bad records
curated/    cleaned Parquet events
analytics/  daily and product-level metrics
reports/    quality and verification JSON reports
```

## 3. Why Use A Corrupted Layer?

I created a corrupted layer because I wanted the pipeline to prove it can handle bad data, not just process clean data.

The raw layer stores the original source unchanged. The corrupted layer is a controlled test input where I inject known data quality issues. This lets me validate whether the Spark quality checks and cleaning logic work correctly.

In real pipelines, bad data often arrives from upstream systems. By injecting controlled bad records, I can test the pipeline behavior in a repeatable way.

The injected problems include:

```text
duplicate rows
negative price
invalid event type
missing timestamp
missing user_id
future timestamp
missing session
```

## 4. Why Spark Instead Of Pandas?

I used Pandas for small preparation tasks, such as sampling 1000 rows from the Kaggle zip file. But I used Spark for the main pipeline because Spark is designed for larger-scale processing.

Even though I tested with 1000 rows on a small EC2 instance, the same Spark jobs can process larger data on EMR, Glue, or a larger EC2 instance.

The key design idea is that I separated development scale from production architecture. I used small data for cost-effective validation, but kept the processing framework scalable.

## 5. Why S3?

S3 is a common data lake storage layer on AWS. It separates storage from compute, so EC2, EMR, Glue, Athena, or other services can read the same data.

I used S3 prefixes to represent pipeline layers:

```text
raw
corrupted
curated
analytics
reports
```

This makes the pipeline easier to reason about and closer to real-world data lake design.

## 6. What Does Airflow Do?

Airflow orchestrates the pipeline. It does not clean or aggregate the data itself.

Spark is the processing engine. S3 is the storage layer. Airflow is the workflow orchestration layer. EC2 is the compute environment.

For the S3 version, Airflow checks that the corrupted input exists in S3, runs the Spark S3 pipeline, and prints the final verification report.

## 7. What Ran On EC2?

On EC2, I installed Java, Python, PySpark, Airflow, Kaggle CLI, and AWS CLI.

I used EC2 to:

```text
download or sample Kaggle data
inject bad records
upload raw and corrupted data to S3
run Spark jobs against S3
orchestrate the S3 pipeline with Airflow
```

## 8. Why Only 1000 Rows?

I used t3.micro for cost control, and it has very limited memory. Running full Spark and Airflow workloads on that instance is not realistic.

So I sampled 1000 rows from the real Kaggle data to validate the pipeline logic. The architecture remains scalable because the Spark jobs and S3 layout are the same for larger data.

For a larger run, I would move to t3.medium for demo scale, or EMR and Glue for production scale.

## 9. What Broke During AWS Deployment?

Several things broke, and they were valuable learning points.

First, SPARK_HOME pointed to the wrong directory. Spark expected the PySpark home folder containing bin/spark-class, but the path initially pointed to site-packages or used a wildcard. I fixed it by resolving the actual PySpark package path.

Second, Spark failed with "No FileSystem for scheme s3." I learned that AWS CLI uses s3:// paths, but Spark uses Hadoop's S3A connector, so Spark needs s3a://. I updated the S3 runner to accept s3:// input and convert it internally to s3a:// for Spark.

Third, the Kaggle dataset was large. On t3.micro, extracting the full CSV was unnecessary, so I sampled directly from the downloaded zip file.

Fourth, I hit a file naming mismatch between ecommerce_events.csv and ecommerce_events_sample.csv. That taught me to make script inputs explicit and print which files are being read.

## 10. Explain s3:// vs s3a://

AWS CLI understands s3:// paths. Spark reads S3 through the Hadoop filesystem layer, and for that the correct scheme is s3a://.

So this works for AWS CLI:

```bash
aws s3 ls s3://bucket/path
```

But Spark needs:

```text
s3a://bucket/path
```

I added the Hadoop AWS package and configured S3A. Then I made the script convert s3:// to s3a:// internally for Spark reads and writes, while still using s3:// for AWS CLI commands.

## 11. How Did You Handle Credentials?

For AWS, the better approach is to attach an IAM role to the EC2 instance with permission to the required S3 prefix. The Spark job uses the default AWS credential provider chain, so it can use the EC2 role.

For Kaggle, I used an access token stored outside the codebase in ~/.kaggle/access_token and passed it through an environment variable.

I avoided putting secrets into source code.

## 12. How Did You Validate The Pipeline?

I validated it at multiple levels.

First, I checked local row counts. For 1000 raw rows, I expect 25 duplicate rows and 5 bad records, so the corrupted file should contain 1030 data rows.

Second, I checked the data quality report to confirm bad records were detected.

Third, I verified that curated Parquet and analytics Parquet outputs were created.

Fourth, I used a verification job to count final curated rows, daily metric rows, and product metric rows, then wrote the result to a JSON report.

The expected row-count logic is:

```text
raw CSV:       1000 data rows
corrupted CSV: 1000 + 25 duplicates + 5 bad rows = 1030 rows
```

## 13. What Analytics Did You Create?

I created daily metrics and product-level metrics.

Daily metrics summarize event volume, purchases, revenue, and active users by date.

Product metrics summarize views, carts, purchases, and revenue by product.

These outputs are written as Parquet so they are efficient to query later.

## 14. How Would You Improve It?

I would improve the project in several ways.

I would add schema validation with Great Expectations or Deequ. I would partition curated data by event_date for faster queries. I would add Airflow retries, alerts, and monitoring. I would register the curated tables in Glue Data Catalog so Athena can query the outputs.

I would also move Spark execution from EC2 to EMR or AWS Glue for production, store secrets in AWS Secrets Manager, add CI/CD, and add unit tests for transformation logic.

## 15. What Would Production Look Like?

For production, I would not run everything manually on one EC2 instance.

I would store data in S3, use Glue or EMR for Spark processing, use MWAA or managed Airflow for orchestration, register curated tables in Glue Data Catalog, query outputs with Athena, and monitor with CloudWatch.

The current project is a cost-conscious prototype, but the folder layout and Spark jobs are designed so they can move to managed AWS services.

## 16. How Did You Use GenAI?

I used GenAI as a build and debugging assistant. It helped me generate scripts, explain errors, compare technology choices, and iterate on the project structure.

But I did not blindly trust it. I validated outputs by running commands, checking row counts, reading error logs, and fixing wrong assumptions.

For example, I caught and fixed issues around SPARK_HOME paths, file naming, Kaggle download behavior, and the difference between s3:// and s3a://.

One specific example was Kaggle authentication. The first setup used the traditional kaggle.json method, which was suggested by GenAI. But when I practiced the workflow myself, I discovered that the newer Kaggle CLI supports an access_token workflow. I updated the project to use ~/.kaggle/access_token and the KAGGLE_API_TOKEN environment variable instead.

This taught me that GenAI output can lag behind tool changes. It can give a useful starting point, but setup instructions still need to be tested against the real command-line behavior.

Another example was SPARK_HOME. The first GenAI-generated setup guessed the PySpark path using a wildcard or returned the parent site-packages directory. That was wrong because Spark needs SPARK_HOME to point to the actual pyspark package directory containing bin/spark-class.

The wrong paths looked like this:

```text
.venv/lib/python3.*/site-packages/pyspark
.venv/lib/python3.12/site-packages
```

The correct path should end with:

```text
site-packages/pyspark
```

I debugged it by checking the error message, inspecting the real package path, and validating that this file existed:

```text
$SPARK_HOME/bin/spark-class
```

The actual code changes look slightly different in different files because they run in different contexts.

In the README setup command, I replaced the hard-coded path:

```bash
export SPARK_HOME="$(pwd)/.venv/lib/python3.12/site-packages/pyspark"
```

with a dynamic shell command:

```bash
export SPARK_HOME="$(python -c 'import pathlib, pyspark; print(pathlib.Path(pyspark.__file__).parent)')"
```

In the Airflow DAG, I could not use shell substitution inside Python module configuration, so I added a helper function:

```python
def default_spark_home() -> str:
    try:
        import pyspark

        return str(pathlib.Path(pyspark.__file__).parent)
    except ImportError:
        return f"{PROJECT_ROOT}/.venv/lib/python3.12/site-packages/pyspark"


SPARK_HOME = os.environ.get("SPARK_HOME", default_spark_home())
```

Both changes solve the same problem: avoid guessing the PySpark location and resolve the real package directory that contains bin/spark-class.

The main lesson is that I treated GenAI output as a hypothesis, not as the final answer. I used it to move faster, but I still verified assumptions through execution, logs, and row-count checks.

## 17. What Would You Do Differently?

I would define file naming conventions earlier. At one point, I had both ecommerce_events.csv and ecommerce_events_sample.csv, which caused the bad-record injection script to read the wrong file.

I would also add stronger command-line validation so scripts print exactly which input and output files they use.

Finally, I would decide earlier which DAG is for local development and which DAG is for S3 cloud execution.

## 18. STAR Story

Situation:

I was moving a local PySpark pipeline to EC2 and S3.

Task:

I needed to make the same pipeline read from S3, write outputs to S3, and remain runnable on a small t3.micro instance.

Action:

I sampled the Kaggle dataset to 1000 rows, uploaded raw and corrupted data to S3, configured Spark with Hadoop AWS dependencies, fixed SPARK_HOME, converted s3:// paths to s3a:// for Spark, and added an Airflow S3 DAG to orchestrate the workflow.

Result:

The pipeline moved from local file processing to cloud-based S3 processing. I also documented the limitations of t3.micro and designed the workflow so it can scale to larger EC2, EMR, or Glue.

## 19. Best Closing Statement

The biggest lesson was that data engineering is not just writing transformations.

A lot of the real work is validating assumptions around file paths, environments, credentials, storage systems, and resource limits.

This project helped me practice an end-to-end data engineering workflow from local development to cloud execution.
